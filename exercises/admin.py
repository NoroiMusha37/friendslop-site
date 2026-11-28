from django import forms
from django.contrib import admin

from common.admin import AdminOwnerInline
from exercises.models import Exercise, ExerciseReview, MuscleCategory, PlanExercise, TrainingPlan


class ExerciseAdminForm(forms.ModelForm):
    muscle_categories = forms.MultipleChoiceField(
        choices=MuscleCategory,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Exercise
        fields = ["name", "description", "muscle_categories", "load_category", "intensity"]


class ExerciseReviewInline(AdminOwnerInline, admin.TabularInline):
    """An archived exercise is read-only, its reviews included."""

    model = ExerciseReview
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")

    def has_add_permission(self, request, obj=None):
        return not (obj and obj.is_archived) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_archived) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_archived) and super().has_delete_permission(request, obj)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    """Exercises are never deleted, and archiving or restoring happens through the API."""

    form = ExerciseAdminForm
    inlines = [ExerciseReviewInline]
    list_display = ("name", "load_category", "intensity", "archived_at")
    list_filter = ("load_category", "intensity")
    search_fields = ("name",)
    readonly_fields = ("archived_at",)

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_archived) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class PlanExerciseInline(admin.TabularInline):
    model = PlanExercise
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("exercise")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    """Plans are immutable and kept for analysis, so here they can only be viewed."""

    inlines = [PlanExerciseInline]
    list_display = ("name", "user", "mode", "created_at")
    list_filter = ("mode",)
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
