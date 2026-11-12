"""
Add this on delete method:

# Character deletion must preserve existing story history.
#
# Before deleting a character, check whether any StoryDialogue references it.
# If references exist, reject the operation with a domain-level exception
# instead of relying on a raw database IntegrityError.
#
# Do not automatically delete or modify existing dialogues to bypass
# the foreign key constraint.
#
# If character removal without history loss is required, implement
# soft deletion (e.g., is_active=False) instead of physical deletion.
#
# Full SessionNarrative deletion is a separate operation and should
# rely on the configured cascading delete relationships.
"""