# Generated by Django 2.2.8 on 2020-02-20 04:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storer', '0003_auto_20181119_0016'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='archivesspace_uri',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='package',
            name='fedora_uri',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='package',
            name='origin',
            field=models.CharField(choices=[('aurora', 'Aurora'), ('legacy_digital', 'Legacy Digital Processing'), ('digitization', 'Digitization')], default='aurora', max_length=20),
        ),
        migrations.AlterField(
            model_name='package',
            name='process_status',
            field=models.CharField(choices=[(10, 'Package downloaded'), (20, 'Package stored'), (25, 'Package data delivered'), (30, 'Package cleaned up')], default=10, max_length=50),
        ),
    ]