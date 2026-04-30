from django.db import transaction

def get_client_ip(request):
    if not request: return ""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip or ""

def log_action(request, action_type, model_name, object_id, object_repr, description, metadata=None, user_override=None):
    """
    Enterprise-grade non-blocking audit logging.
    If logging fails or a transaction rolls back, main operation remains unaffected.
    """
    from .models import AuditLog
    
    # 1. Prep data outside on_commit to capture current request state
    if user_override:
        user = user_override
    else:
        user = request.user if request and request.user.is_authenticated else None
    
    school = user.school if user and hasattr(user, 'school') else None
    ip_address = get_client_ip(request) if request else ""
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ""
    meta = metadata or {}

    def _create_log():
        try:
            from django.db import connection
            # Extra safeguard: ensure table exists before trying to create
            table_name = AuditLog._meta.db_table
            if table_name not in connection.introspection.table_names():
                print(f"⚠️ Audit Log Skipped: Table {table_name} does not exist. Please run migrations.")
                return

            AuditLog.objects.create(
                user=user,
                school=school,
                action_type=action_type,
                model_name=model_name,
                object_id=str(object_id),
                object_repr=str(object_repr),
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=meta
            )
            print(f"✅ Audit Log Created Successfully: {action_type} on {model_name} ({object_repr})")
        except Exception as e:
            # Crucial: NEVER let audit logging break the main transaction
            print(f"❌ Audit Log Failed: {str(e)}")

    # 2. Defer execution until after successful commit
    # If not in a transaction (e.g. simple GET), it runs immediately
    transaction.on_commit(_create_log)

