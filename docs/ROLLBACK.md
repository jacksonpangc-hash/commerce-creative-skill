# Upgrade and rollback

The installer refuses to overwrite `commerce-creative`. Before an update, compare the installed Skill with its `installation-manifest.json`, archive local modifications outside the agent's skills directory, then install the new version. Do not restore a whole old global configuration to remove one skill.

To disable this new Skill, move only its directory outside the client's skills directory. Preserve its install manifest, project `.commerce` data and original Clipcat. Removing a pip installation is optional and applies only to the Python environment used for this project. No global shell or Codex configuration needs reversal.

Existing vendor tasks, posts and accepted schedules are external state: disabling this Skill does not cancel them. Reconcile using saved original task ids/creator-center works and the vendor's supported controls. Never remove local locks merely to retry an uncertain submission.

Publishing the open-source repository does not create provider jobs or social posts. Disabling the local Skill does not withdraw public GitHub source. Repository visibility or deletion is a separate user decision; do not alter unrelated repositories.
