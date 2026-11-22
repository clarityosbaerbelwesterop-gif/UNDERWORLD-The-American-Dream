# Shared: what counts as a *real* error in a `godot --headless --import` log.
#
# Every test runner must fail on Godot ERROR lines, but this sandbox Godot is compiled with
# fontconfig=no (Docs/TOOLCHAIN_SANDBOX.md). The editor theme therefore logs
#
#   ERROR: Godot was compiled without fontconfig, system font support is disabled.
#      at: get_system_font_path (platform/linuxbsd/os_linuxbsd.cpp:892)
#
# on every headless start - before any project code runs. That line is a property of the
# toolchain, not of the project, so it is filtered out here, in one place, by exact message.
# Anything else (missing resource, script parse error, broken .tscn, ...) still fails the run.
#
# Usage:  errs="$(godot_log_errors "$LOG")"; [ -z "$errs" ] || fail "$errs"
godot_log_errors() {
	local log="$1"
	[ -f "$log" ] || return 0
	grep -E '^(ERROR|SCRIPT ERROR|USER ERROR):' "$log" \
		| grep -v 'Godot was compiled without fontconfig' \
		| grep -v 'os_linuxbsd\.cpp:892'
}
