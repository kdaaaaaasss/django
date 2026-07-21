from random import choice

from django.db import models

# on_delete=models.CASCADE


class Housing(models.Model):
    # owner_id = models.ForeignKey(Users)
    title = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=128, blank=True)
    address = models.TextField(blank=True)
    price = models.DecimalField(max_digits=11, decimal_places=2)
    rooms = models.PositiveIntegerField(default=1)
    rating = models.PositiveIntegerField

    def __str__(self):
        return f"{self.title} | {self.rooms}"

class Photo(models.Model):
    # image = models.ImageField()
    housing_id = models.ForeignKey(Housing, on_delete=models.CASCADE) #

class Booking(models.Model):
    # user_id =
    # housing_id =
    pass

class Specifications(models.Model):
    # housing_id
    # specification_id
    pass

class Specification(models.Model):
    name = models.CharField(max_length=64, unique=True)


# Create your models here.