package bridge

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type publicWSMessage struct {
	Type            string                  `json:"type"`
	OK              bool                    `json:"ok,omitempty"`
	ProtocolVersion string                  `json:"protocol_version,omitempty"`
	Time            int64                   `json:"time,omitempty"`
	Limit           int                     `json:"limit,omitempty"`
	Error           string                  `json:"error,omitempty"`
	Event           *PublicMessageEnvelope  `json:"event,omitempty"`
	Events          []PublicMessageEnvelope `json:"events,omitempty"`
}

func (s *HTTPServer) publicWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgradeWebSocket(w, r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "websocket_upgrade_failed", err.Error())
		return
	}
	defer conn.close()

	ctx, cancel := context.WithCancel(r.Context())
	defer cancel()
	auth, _ := publicAPIAuthFromContext(r.Context())

	outgoing := make(chan publicWSMessage, 16)
	go s.readPublicWS(ctx, cancel, conn, outgoing, auth)

	outgoing <- publicWSMessage{Type: "hello", OK: true, ProtocolVersion: "v1", Time: time.Now().Unix()}
	if replay := wsReplayLimit(r.URL.Query().Get("replay"), 0); replay > 0 {
		outgoing <- publicWSMessage{Type: "replay", OK: true, ProtocolVersion: "v1", Time: time.Now().Unix(), Events: s.publicRecentEvents(replay, auth)}
	}

	events := s.service.Hub().Subscribe(ctx)
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case msg := <-outgoing:
			if !conn.writeJSON(msg) {
				return
			}
		case event, ok := <-events:
			if !ok {
				return
			}
			if !publicAPIEventAllowed(auth, event) {
				continue
			}
			clean := publicEventMessageEnvelope(event)
			outgoing <- publicWSMessage{Type: "message", OK: true, ProtocolVersion: "v1", Time: time.Now().Unix(), Event: &clean}
		case <-ticker.C:
			if !conn.writeControl(wsOpPing, []byte("ping")) {
				return
			}
			outgoing <- publicWSMessage{Type: "ping", Time: time.Now().Unix()}
		}
	}
}

func (s *HTTPServer) readPublicWS(ctx context.Context, cancel context.CancelFunc, conn *wsConn, outgoing chan<- publicWSMessage, auth publicAPIAuth) {
	defer cancel()
	for {
		payload, op, err := conn.readFrame()
		if err != nil {
			return
		}
		switch op {
		case wsOpClose:
			return
		case wsOpPing:
			if !conn.writeControl(wsOpPong, payload) {
				return
			}
		case wsOpPong:
			continue
		case wsOpText:
			var msg publicWSMessage
			if err := json.Unmarshal(payload, &msg); err != nil {
				outgoing <- publicWSMessage{Type: "error", Error: "invalid json: " + err.Error(), Time: time.Now().Unix()}
				continue
			}
			switch strings.ToLower(strings.TrimSpace(msg.Type)) {
			case "ping":
				outgoing <- publicWSMessage{Type: "pong", OK: true, Time: time.Now().Unix()}
			case "replay":
				limit := msg.Limit
				if limit <= 0 {
					limit = 20
				}
				if limit > 200 {
					limit = 200
				}
				outgoing <- publicWSMessage{Type: "replay", OK: true, ProtocolVersion: "v1", Time: time.Now().Unix(), Events: s.publicRecentEvents(limit, auth)}
			case "":
				outgoing <- publicWSMessage{Type: "error", Error: "type is required", Time: time.Now().Unix()}
			default:
				outgoing <- publicWSMessage{Type: "error", Error: "unknown message type", Time: time.Now().Unix()}
			}
		}
	}
}

func (s *HTTPServer) publicRecentEvents(limit int, auth publicAPIAuth) []PublicMessageEnvelope {
	events := s.service.Hub().Recent(limit)
	out := make([]PublicMessageEnvelope, 0, len(events))
	for _, event := range events {
		if !publicAPIEventAllowed(auth, event) {
			continue
		}
		out = append(out, publicEventMessageEnvelope(event))
	}
	return out
}

func publicAPIEventAllowed(auth publicAPIAuth, event MessageEvent) bool {
	return auth.Device == "" || event.Device == auth.Device
}

func wsReplayLimit(raw string, fallback int) int {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil || value < 0 {
		return fallback
	}
	if value > 200 {
		return 200
	}
	return value
}
