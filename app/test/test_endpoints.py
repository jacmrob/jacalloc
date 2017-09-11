from app import app, db
from flask import url_for
import unittest

class FlaskTest(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()