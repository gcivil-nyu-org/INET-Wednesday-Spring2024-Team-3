from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from user.models import FriendRequest, Friendship

class FriendModelTests(TestCase):
    def setUp(self):
        # Create two users for testing friendship features
        self.user1 = User.objects.create_user(username='user1', password='testpass1')
        self.user2 = User.objects.create_user(username='user2', password='testpass2')

    def test_friend_request_creation(self):
        # Create a friend request from user1 to user2
        friend_request = FriendRequest.objects.create(
            from_user=self.user1,
            to_user=self.user2
        )
        self.assertEqual(friend_request.from_user, self.user1)
        self.assertEqual(friend_request.to_user, self.user2)
        self.assertEqual(friend_request.status, 'pending')

    def test_friend_request_status(self):
        # Create a friend request and then accept it
        friend_request = FriendRequest.objects.create(
            from_user=self.user1,
            to_user=self.user2
        )
        friend_request.status = 'accepted'
        friend_request.save()

        # Fetch the updated friend request from the database
        updated_friend_request = FriendRequest.objects.get(pk=friend_request.pk)
        self.assertEqual(updated_friend_request.status, 'accepted')

    def test_friendship_creation(self):
        # Create a friendship between user1 and user2
        friendship = Friendship.objects.create(
            user1=self.user1,
            user2=self.user2
        )
        self.assertTrue(Friendship.objects.filter(user1=self.user1, user2=self.user2).exists())

    def test_unique_friendship(self):
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(user1=self.user1, user2=self.user2)

    def tearDown(self):
        # Your teardown logic, if you have any
        pass

