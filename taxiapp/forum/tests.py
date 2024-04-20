from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import Category, Post, Topic, Comment, Vote


class CategoryModelTest(TestCase):
    def test_string_representation(self):
        category = Category(name="Test Category")
        self.assertEqual(str(category), "Test Category")


class PostModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.category = Category.objects.create(name="Test Category")
        self.topic = Topic.objects.create(name="Test Topic")

    def test_post_creation(self):
        post = Post.objects.create(
            user=self.user,
            title="Test Post",
            content="This is a test post content.",
            category=self.category,
            topic=self.topic,
        )
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.content, "This is a test post content.")
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.topic, self.topic)
        self.assertEqual(post.score, 0)


class TopicModelTest(TestCase):
    def test_string_representation(self):
        topic = Topic(name="Test Topic")
        self.assertEqual(str(topic), "Test Topic")


class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.post = Post.objects.create(
            user=self.user,
            title="Test Post",
            content="This is a test post content.",
        )

    def test_comment_creation(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            content="This is a test comment.",
        )
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.content, "This is a test comment.")


class VoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.post = Post.objects.create(
            user=self.user,
            title="Test Post",
            content="This is a test post content.",
        )

    def test_vote_creation(self):
        vote = Vote.objects.create(
            user=self.user,
            post=self.post,
            vote_type="upvote",
        )
        self.assertEqual(vote.user, self.user)
        self.assertEqual(vote.post, self.post)
        self.assertEqual(vote.vote_type, "upvote")
