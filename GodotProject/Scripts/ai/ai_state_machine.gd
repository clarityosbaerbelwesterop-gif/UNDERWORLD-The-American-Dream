# UNDERWORLD - data-driven state machine (T-AI-01). The transition table comes from
# AIProfile.transitions: { state: { event: next_state } }, "*" = any state. States with an entry
# in AIProfile.state_timeouts receive the event "timeout" after that many seconds.
# The machine only decides WHICH state; NPCController implements what each state does.
class_name AIStateMachine
extends RefCounted

signal state_changed(from: String, to: String, event: String)

var table: Dictionary
var timeouts: Dictionary
var state := ""
var time_in_state := 0.0
## [from, to, event] of every transition (debug / tests).
var history: Array = []
var _timeout_sent := false

func _init(transitions: Dictionary, state_timeouts: Dictionary, initial: String) -> void:
	table = transitions
	timeouts = state_timeouts
	state = initial

func next_state_for(event: String) -> String:
	var row: Dictionary = table.get(state, {})
	if row.has(event):
		return row[event]
	var any: Dictionary = table.get("*", {})
	if any.has(event):
		return any[event]
	return ""

## Returns true if the event caused a transition (a self-transition re-enters the state).
func send(event: String) -> bool:
	var n := next_state_for(event)
	if n == "":
		return false
	_change(n, event)
	return true

func force(to: String, reason: String) -> void:
	_change(to, reason)

func tick(delta: float) -> void:
	time_in_state += delta
	if not _timeout_sent and timeouts.has(state) and time_in_state >= float(timeouts[state]):
		_timeout_sent = true
		send("timeout")

func _change(to: String, event: String) -> void:
	var from := state
	state = to
	time_in_state = 0.0
	_timeout_sent = false
	history.append([from, to, event])
	state_changed.emit(from, to, event)

## Static check of a table: unknown states, bad initial state, timeouts on unknown states.
static func validate(transitions: Dictionary, state_timeouts: Dictionary, initial: String, known: PackedStringArray) -> PackedStringArray:
	var errs := PackedStringArray()
	if not known.has(initial):
		errs.append("initial state '%s' unknown" % initial)
	for s in transitions.keys():
		if s != "*" and not known.has(s):
			errs.append("table row '%s' is not a known state" % s)
		var row = transitions[s]
		if not row is Dictionary:
			errs.append("row '%s' is not a Dictionary" % s)
			continue
		for ev in row.keys():
			if not known.has(row[ev]):
				errs.append("'%s' --%s--> unknown state '%s'" % [s, ev, row[ev]])
	for s in state_timeouts.keys():
		if not known.has(s):
			errs.append("timeout for unknown state '%s'" % s)
	return errs
