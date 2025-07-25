# Generated by Django 5.2.4 on 2025-07-13 23:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_alter_course_skills_alter_enrollment_grade_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='video',
            field=models.FileField(blank=True, null=True, upload_to='lesson_videos/'),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='Bundle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=6)),
                ('courses', models.ManyToManyField(to='catalog.course')),
            ],
        ),
    ]
