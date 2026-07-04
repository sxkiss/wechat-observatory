// @input: context, strings, sync, time; bridge outbox request and reply domain types
// @output: In-memory outbox backend with lease, ack, and lane-aware batch selection behavior
// @position: Default non-MySQL outbox implementation used by the bridge service and tests
// @auto-doc: Update header and folder INDEX.md when this file changes
package bridge

import (
	"context"
	"strings"
	"sync"
	"time"
)

const defaultOutboxLease = 60 * time.Second

type MemoryOutbox struct {
	mu     sync.Mutex
	nextID int64
	items  []memoryOutboxItem
	now    func() time.Time
}

type memoryOutboxItem struct {
	ModuleOutboxItem
	leaseUntil time.Time
}

func NewMemoryOutbox() *MemoryOutbox {
	return &MemoryOutbox{now: time.Now}
}

func (o *MemoryOutbox) EnqueueReply(_ context.Context, action ReplyAction) (ModuleOutboxItem, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.nextID++
	now := o.now()
	item := memoryOutboxItem{
		ModuleOutboxItem: ModuleOutboxItem{
			ID:          o.nextID,
			Device:      action.Device,
			OwnerWxID:   action.OwnerWxID,
			WxID:        action.WxID,
			Kind:        firstNonEmpty(action.Kind, OutboxKindText),
			Text:        action.Text,
			PayloadJSON: append([]byte(nil), action.PayloadJSON...),
			MediaKind:   action.MediaKind,
			MediaMime:   action.MediaMime,
			MediaName:   action.MediaName,
			MediaURL:    action.MediaURL,
			MediaSize:   action.MediaSize,
			Status:      "pending",
			CreatedAt:   formatRFC3339(now),
			UpdatedAt:   formatRFC3339(now),
		},
	}
	o.items = append(o.items, item)
	return item.ModuleOutboxItem, nil
}

func (o *MemoryOutbox) PollReplyActions(_ context.Context, req ModulePollRequest) ([]ModuleOutboxItem, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	limit := req.Limit
	if limit <= 0 {
		limit = 20
	}
	now := o.now()
	candidates := make([]OutboxLeaseCandidate, 0, len(o.items))
	for i := range o.items {
		if o.items[i].Device != req.Device {
			continue
		}
		if strings.TrimSpace(req.WxID) != "" && strings.TrimSpace(o.items[i].OwnerWxID) != strings.TrimSpace(req.WxID) {
			continue
		}
		if o.items[i].Status != "pending" && !(o.items[i].Status == "leased" && o.items[i].leaseUntil.Before(now)) {
			continue
		}
		candidates = append(candidates, OutboxLeaseCandidate{
			ID:       o.items[i].ID,
			Position: i,
			WxID:     o.items[i].WxID,
			Kind:     o.items[i].Kind,
		})
	}
	selectedCandidates := SelectOutboxLeaseCandidates(candidates, limit)
	out := make([]ModuleOutboxItem, 0, len(selectedCandidates))
	for _, candidate := range selectedCandidates {
		i := candidate.Position
		o.items[i].Status = "leased"
		o.items[i].AttemptCount++
		o.items[i].leaseUntil = now.Add(defaultOutboxLease)
		o.items[i].UpdatedAt = formatRFC3339(now)
		out = append(out, o.items[i].ModuleOutboxItem)
	}
	return out, nil
}

func (o *MemoryOutbox) AckReplyActions(_ context.Context, req ModuleAckRequest) ([]ModuleOutboxItem, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	acks := map[int64]ModuleAckItem{}
	for _, item := range req.Items {
		acks[item.ID] = item
	}
	now := o.now()
	out := []ModuleOutboxItem{}
	for i := range o.items {
		ack, ok := acks[o.items[i].ID]
		if !ok || o.items[i].Device != req.Device {
			continue
		}
		if strings.TrimSpace(req.WxID) != "" && strings.TrimSpace(o.items[i].OwnerWxID) != strings.TrimSpace(req.WxID) {
			continue
		}
		o.items[i].Status = ack.Status
		o.items[i].LastError = ack.Error
		if ack.ChatRecordID > 0 {
			o.items[i].ChatRecordID = ack.ChatRecordID
		}
		o.items[i].leaseUntil = time.Time{}
		o.items[i].UpdatedAt = formatRFC3339(now)
		out = append(out, o.items[i].ModuleOutboxItem)
	}
	return out, nil
}

func (o *MemoryOutbox) GetReplyAction(_ context.Context, id int64) (ModuleOutboxItem, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	for _, item := range o.items {
		if item.ID == id {
			return item.ModuleOutboxItem, nil
		}
	}
	return ModuleOutboxItem{}, ErrOutboxItemNotFound
}

func formatRFC3339(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.UTC().Format(time.RFC3339)
}
