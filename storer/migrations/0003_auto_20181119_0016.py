# Generated by Django 2.0.8 on 2018-11-19 00:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storer', '0002_package_process_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='internal_sender_identifier',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AlterField(
            model_name='package',
            name='process_status',
            field=models.CharField(choices=[(10, 'Package downloaded'), (20, 'Package stored'), (30, 'Package cleaned up')], default=10, max_length=50),
        ),
    ]
