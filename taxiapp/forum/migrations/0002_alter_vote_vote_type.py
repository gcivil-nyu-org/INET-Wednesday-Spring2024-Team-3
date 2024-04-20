# Generated by Django 3.2.24 on 2024-04-20 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vote',
            name='vote_type',
            field=models.CharField(choices=[('upvote', 'Upvote'), ('downvote', 'Downvote'), ('neutral', 'Neutral')], default='neutral', max_length=10),
        ),
    ]