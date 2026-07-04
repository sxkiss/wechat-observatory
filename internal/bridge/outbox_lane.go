// @input: strings, sort; module outbox item metadata from the bridge domain
// @output: Lane-aware lease candidate selection shared by in-memory and MySQL outbox backends
// @position: Keeps same `wxid + kind` sends serialized while maximizing per-batch lane spread
// @auto-doc: Update header and folder INDEX.md when this file changes
package bridge

import (
	"sort"
	"strings"
)

type OutboxLeaseCandidate struct {
	ID       int64
	Position int
	WxID     string
	Kind     string
}

func SelectOutboxLeaseCandidates(candidates []OutboxLeaseCandidate, limit int) []OutboxLeaseCandidate {
	if limit <= 0 || len(candidates) == 0 {
		return nil
	}
	if limit >= len(candidates) {
		out := append([]OutboxLeaseCandidate(nil), candidates...)
		sort.Slice(out, func(i, j int) bool {
			return out[i].Position < out[j].Position
		})
		return out
	}

	lanes := map[string][]OutboxLeaseCandidate{}
	laneOrder := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		laneKey := outboxLaneKey(candidate.WxID, candidate.Kind)
		if _, ok := lanes[laneKey]; !ok {
			laneOrder = append(laneOrder, laneKey)
		}
		lanes[laneKey] = append(lanes[laneKey], candidate)
	}

	selected := make([]OutboxLeaseCandidate, 0, limit)
	for len(selected) < limit {
		progressed := false
		for _, laneKey := range laneOrder {
			queue := lanes[laneKey]
			if len(queue) == 0 {
				continue
			}
			selected = append(selected, queue[0])
			lanes[laneKey] = queue[1:]
			progressed = true
			if len(selected) >= limit {
				break
			}
		}
		if !progressed {
			break
		}
	}

	sort.Slice(selected, func(i, j int) bool {
		return selected[i].Position < selected[j].Position
	})
	return selected
}

func outboxLaneKey(wxid string, kind string) string {
	wxid = strings.TrimSpace(wxid)
	kind = strings.TrimSpace(kind)
	if kind == "" {
		kind = OutboxKindText
	}
	return wxid + "|" + kind
}
