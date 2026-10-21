"""Option descriptor parsing (`scanimage --get-options`) — milestone 2.

Will parse machine-readable option descriptors (name, type, constraints,
current/default values) into list[OptionDescriptor], and build the `-o
name=value` arguments used when scanning.
"""
