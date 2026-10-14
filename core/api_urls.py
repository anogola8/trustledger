from django.urls import path

from accounts import api as accounts
from attestations import api as atts
from disputes import api as disputes
from employers import api as employers
from notifications import api as notifications
from trustscore import api as trust
from verification import api as verification
from workers import api as workers

urlpatterns = [
    path('auth/register/', accounts.RegisterView.as_view()),
    path('auth/login/', accounts.LoginView.as_view()),
    path('auth/logout/', accounts.LogoutView.as_view()),
    path('auth/me/', accounts.MeView.as_view()),
    path('workers/me/', workers.WorkerMeView.as_view()),
    path('workers/me/skills/', workers.SkillListCreate.as_view()),
    path('workers/<slug:slug>/', workers.WorkerPublicView.as_view()),
    path('workers/<slug:slug>/trust-score/', trust.TrustScoreView.as_view()),
    path('employers/me/', employers.EmployerMeView.as_view()),
    path('employers/', employers.EmployerListView.as_view()),
    path('employers/<int:pk>/approve/', employers.EmployerApproveView.as_view()),
    path('attestations/', atts.AttestationListCreate.as_view()),
    path('attestations/<uuid:pk>/', atts.AttestationDetail.as_view()),
    path('attestations/<uuid:pk>/confirm/', atts.AttestationAction.as_view(action='confirm')),
    path('attestations/<uuid:pk>/reject/', atts.AttestationAction.as_view(action='reject')),
    path('attestations/<uuid:pk>/revoke/', atts.AttestationAction.as_view(action='revoke')),
    path('verify/<str:code>/', verification.VerifyAPIView.as_view()),
    path('disputes/', disputes.DisputeListCreate.as_view()),
    path('disputes/<int:pk>/resolve/', disputes.DisputeResolveView.as_view()),
    path('notifications/', notifications.NotificationList.as_view()),
    path('notifications/<int:pk>/read/', notifications.NotificationRead.as_view()),
]
