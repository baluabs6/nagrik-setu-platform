import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="issue",
            name="description",
            field=models.TextField(
                validators=[
                    django.core.validators.MinLengthValidator(10),
                    django.core.validators.MaxLengthValidator(2000),
                ]
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="attachment_verified",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Set true by the upload-validation Lambda once it confirms the object's real "
                    "content matches an allowed image type and strips EXIF/GPS metadata. Until "
                    "then the photo is not considered safe to serve publicly."
                ),
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="ai_suggested_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("roads", "Roads & Potholes"),
                    ("water", "Water Supply"),
                    ("garbage", "Garbage & Sanitation"),
                    ("power", "Power Outages"),
                    ("lighting", "Street Lighting"),
                    ("transport", "Public Transport"),
                    ("pollution", "Air & Noise Pollution"),
                    ("grievance", "Corruption & Grievances"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="ai_urgency",
            field=models.CharField(
                blank=True,
                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                default="",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="ai_confidence",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="issue",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Set by the AI duplicate-detection agent when this report closely matches an "
                    "existing open issue in the same locality/category."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicates",
                to="issues.issue",
            ),
        ),
    ]
