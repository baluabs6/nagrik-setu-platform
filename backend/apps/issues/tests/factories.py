import factory
from apps.issues.models import Issue


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    category = Issue.Category.ROADS
    locality = factory.Faker("city")
    description = factory.Faker("sentence")
