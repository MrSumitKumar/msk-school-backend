from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admins.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'super_admin')

class IsSchoolAdmin(permissions.BasePermission):
    """
    Allows access only to school admins.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'school_admin')

class IsTeacher(permissions.BasePermission):
    """
    Allows access only to teachers.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'teacher')

class IsStudent(permissions.BasePermission):
    """
    Allows access only to students.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'student')

class IsSchoolMember(permissions.BasePermission):
    """
    Ensures the user belongs to the school context being accessed.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'super_admin':
            return True
        
        # Determine school of the object
        obj_school = None
        if hasattr(obj, 'school'):
            obj_school = obj.school
        elif hasattr(obj, 'user') and hasattr(obj.user, 'school'):
            obj_school = obj.user.school
            
        return bool(obj_school and obj_school == request.user.school)

class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['super_admin', 'school_admin', 'teacher'])

class IsSuperAdminOrSchoolAdmin(permissions.BasePermission):
    """Allows access only to super_admin or school_admin."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in ['super_admin', 'school_admin']
        )

class GlobalTenantPermission(permissions.BasePermission):
    """
    Globally checks if the requested module is unlocked in the school's active subscription,
    and blocks mutations if the subscription is expired.
    """
    message = "Feature locked or subscription expired."

    def has_permission(self, request, view):
        if not request.user or request.user.is_anonymous or getattr(request.user, 'role', '') == 'super_admin':
            return True
            
        path = request.path
        # Allow password change and me-info even if expired
        if 'change-password' in path or 'accounts/me' in path:
            return True

        required_module = None
        
        # Map URL paths to modules
        if '/api/fees/' in path:
            required_module = 'fees'
        elif '/api/exams/' in path:
            required_module = 'exams'
        elif '/api/timetable/' in path:
            required_module = 'timetable'
        elif 'reports' in path: 
            required_module = 'reports'
        elif 'analytics' in path:
            required_module = 'analytics'
            
        school = getattr(request.user, 'school', None)
        if not school:
            return True
            
        subscription = getattr(school, 'active_subscription', None)
        
        # Expiry Check: restrict mutations if expired or missing
        if not subscription or not subscription.is_active or subscription.status == 'expired':
            if request.method not in ['GET', 'HEAD', 'OPTIONS']:
                self.message = "Your subscription has expired. Please renew."
                return False
                
        # Feature Lock Check
        if subscription and subscription.is_active and subscription.plan and required_module:
            unlocked = subscription.plan.unlocked_modules
            # Parse JSON string from TextField if needed
            if isinstance(unlocked, str):
                try:
                    import json
                    unlocked = json.loads(unlocked)
                except Exception:
                    unlocked = []
            if isinstance(unlocked, list) and required_module not in unlocked:
                self.message = f"Feature '{required_module}' is locked. Upgrade your plan."
                return False
                
        return True


# Backward-compatible alias for existing imports
IsAdminUser = IsSuperAdminOrSchoolAdmin

