"""Server-only Supabase Auth admin adapter.

Kept as a small compatibility module so composition roots can depend on an
Auth-specific boundary without importing the retention workflow.
"""

from yom_awel.persistence.retention import SupabaseAuthAdminClient, SupabaseRetentionError

__all__ = ["SupabaseAuthAdminClient", "SupabaseRetentionError"]
