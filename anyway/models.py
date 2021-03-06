#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging

from .constants import CONST
from collections import namedtuple
from sqlalchemy import Column, BigInteger, Integer, String, Boolean, Float, ForeignKey, DateTime, Text, Index, desc, sql, Table, \
    ForeignKeyConstraint, func, and_
from sqlalchemy.orm import relationship, load_only, backref
from .utilities import init_flask, decode_hebrew
from flask_sqlalchemy import SQLAlchemy
from six import iteritems
from geoalchemy2 import Geometry


import datetime
from . import localization
from .database import Base
from flask_security import UserMixin, RoleMixin
from geoalchemy2 import Geometry

app = init_flask()
db = SQLAlchemy(app)

MarkerResult = namedtuple('MarkerResult', ['markers', 'total_records'])

db_encoding = 'utf-8'

logging.basicConfig(level=logging.DEBUG)

roles_users = Table('roles_users', Base.metadata,
        Column('user_id', Integer(), ForeignKey('users.id')),
        Column('role_id', Integer(), ForeignKey('roles.id')))

class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(BigInteger(), primary_key=True)
    email = Column(String(120), unique=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    access_token = Column(String(100))
    username = Column(String(50), unique=True)
    facebook_id = Column(String(50))
    facebook_url = Column(String(100))
    is_admin = Column(Boolean(), default=False)
    new_features_subscription = Column(Boolean(), default=False)
    password = Column(String(256))
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    social_id = Column(String(64), nullable=True, unique=True)
    nickname = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=True)
    roles = relationship('Role', secondary=roles_users,
                            backref=backref('users', lazy='dynamic'))

    def serialize(self):
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "facebook_id": self.facebook_id,
            "facebook_url": self.facebook_url,
            "is_admin": self.is_admin,
            "new_features_subscription": self.new_features_subscription
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

class LocationSubscribers(Base, UserMixin):
    __tablename__ = "locationsubscribers"
    id = Column(BigInteger(), primary_key=True)
    email = Column(String(120))
    first_name = Column(String(50))
    last_name = Column(String(50))
    ne_lng = Column(Float(), nullable=True)
    ne_lat = Column(Float(), nullable=True)
    sw_lng = Column(Float(), nullable=True)
    sw_lat = Column(Float(), nullable=True)

    def serialize(self):
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "ne_lng": self.ne_lng,
            "ne_lat": self.ne_lat,
            "sw_lng": self.sw_lng,
            "sw_lat": self.sw_lat
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

class Role(Base, RoleMixin):
    __tablename__ = "roles"
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

    def __unicode__(self):
        return self.name

class Point(object):
    id = Column(Integer(), primary_key=True)
    latitude = Column(Float())
    longitude = Column(Float())

class MarkerMixin(Point):
    type = Column(Integer())
    title = Column(String(100))
    created = Column(DateTime, default=datetime.datetime.now, index=True)

    __mapper_args__ = {
        'polymorphic_on': type
    }

    @staticmethod
    def format_description(field, value):
        # if the field's value is a static localizable field, fetch it.
        if field in localization.get_supported_tables():
            value = decode_hebrew(localization.get_field(field, value), db_encoding)
        name = decode_hebrew(localization.get_field(field), db_encoding)
        return u"{0}: {1}".format(name, value)

class HighlightPoint(Point, Base):
    __tablename__ = "highlight_markers"
    __table_args__ = (
        Index('highlight_long_lat_idx', 'latitude', 'longitude'),
    )

    created = Column(DateTime, default=datetime.datetime.now)
    type = Column(Integer())

    def serialize(self):
        return {
            "id": str(self.id),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "type": self.type,
        }

    def update(self, data):
        self.type = data["type"]
        self.latitude = data["latitude"]
        self.longitude = data["longitude"]

    @classmethod
    def parse(cls, data):
        return cls(
            type=data["type"],
            latitude=data["latitude"],
            longitude=data["longitude"]
        )

class AccidentMarker(MarkerMixin, Base):
    __tablename__ = "markers"
    __table_args__ = (
        Index('acc_long_lat_idx', 'latitude', 'longitude'),
        Index('id_idx_markers', 'id', unique=False),
        Index('provider_and_id_idx_markers', 'provider_and_id', unique=True),
        Index('idx_markers_geom', 'geom', unique=False),

    )

    __mapper_args__ = {
        'polymorphic_identity': CONST.MARKER_TYPE_ACCIDENT
    }
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer(), primary_key=True)
    description = Column(Text())
    subtype = Column(Integer())
    severity = Column(Integer())
    address = Column(Text())
    locationAccuracy = Column(Integer())
    roadType = Column(Integer())
    roadShape = Column(Integer())
    dayType = Column(Integer())
    unit = Column(Integer())
    mainStreet = Column(Text())
    secondaryStreet = Column(Text())
    junction = Column(Text())
    one_lane = Column(Integer())
    multi_lane = Column(Integer())
    speed_limit = Column(Integer())
    intactness = Column(Integer())
    road_width = Column(Integer())
    road_sign = Column(Integer())
    road_light = Column(Integer())
    road_control = Column(Integer())
    weather = Column(Integer())
    road_surface = Column(Integer())
    road_object = Column(Integer())
    object_distance = Column(Integer())
    didnt_cross = Column(Integer())
    cross_mode = Column(Integer())
    cross_location = Column(Integer())
    cross_direction = Column(Integer())
    involved = relationship("Involved", foreign_keys="Involved.accident_id")
    vehicles = relationship("Vehicle", foreign_keys="Vehicle.accident_id")
    video_link = Column(Text())
    road1 = Column(Integer())
    road2 = Column(Integer())
    km = Column(Float)
    yishuv_symbol = Column(Integer())
    geo_area = Column(Integer())
    day_night = Column(Integer())
    day_in_week = Column(Integer())
    traffic_light = Column(Integer())
    region = Column(Integer())
    district = Column(Integer())
    natural_area = Column(Integer())
    minizipali_status = Column(Integer())
    yishuv_shape = Column(Integer())
    street1 = Column(Integer())
    street2 = Column(Integer())
    home = Column(Integer())
    urban_intersection = Column(Integer())
    non_urban_intersection = Column(Integer())
    accident_year = Column(Integer())
    accident_month = Column(Integer())
    accident_day = Column(Integer())
    accident_hour_raw = Column(Integer())
    accident_hour = Column(Integer())
    accident_minute = Column(Integer())
    geom = Column(Geometry('POINT'))

    @staticmethod
    def json_to_description(msg):
        description = json.loads(msg, encoding=db_encoding)
        return "\n".join([AccidentMarker.format_description(field, value) for field, value in iteritems(description)])

    def serialize(self, is_thin=False):
        fields = {
            "id": str(self.id),
            "provider_code": self.provider_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "severity": self.severity,
            "locationAccuracy": self.locationAccuracy,
            "created": self.created.isoformat(),
        }
        if not is_thin:
            fields.update({
                "title": self.title,
                "address": self.address,
                "type": self.type,
                "subtype": self.subtype,
                "roadType": self.roadType,
                "roadShape": self.roadShape,
                "dayType": self.dayType,
                "unit": self.unit,
                "mainStreet": self.mainStreet,
                "secondaryStreet": self.secondaryStreet,
                "junction": self.junction,
            })
            # United Hatzala accidents description are not json:
            if self.provider_code == CONST.UNITED_HATZALA_CODE:
                fields.update({"description": self.description})
            else:
                fields.update({"description": AccidentMarker.json_to_description(self.description)})

            optional = {
                "one_lane": self.one_lane,
                "multi_lane": self.multi_lane,
                "speed_limit": self.speed_limit,
                "intactness": self.intactness,
                "road_width": self.road_width,
                "road_sign": self.road_sign,
                "road_light": self.road_light,
                "road_control": self.road_control,
                "weather": self.weather,
                "road_surface": self.road_surface,
                "road_object": self.road_object,
                "object_distance": self.object_distance,
                "didnt_cross": self.didnt_cross,
                "cross_mode": self.cross_mode,
                "cross_location": self.cross_location,
                "cross_direction": self.cross_direction,
                "video_link": self.video_link,
                "road1": self.road1,
                "road2": self.road2,
                "km": self.km
            }
            for name, value in iteritems(optional):
                if value != 0:
                    fields[name] = value
        return fields

    def update(self, data, current_user):
        self.title = data["title"]
        self.description = data["description"]
        self.type = data["type"]
        self.latitude = data["latitude"]
        self.longitude = data["longitude"]

        self.put()

    @staticmethod
    def bounding_box_query(is_thin=False, yield_per=None, involved_and_vehicles=False, **kwargs):

        # example:
        # ne_lat=32.36292402647484&ne_lng=35.08873443603511&sw_lat=32.29257266524761&sw_lng=34.88445739746089
        # >>>  m = AccidentMarker.bounding_box_query(32.36, 35.088, 32.292, 34.884)
        # >>> m.count()
        # 250

        approx = kwargs.get('approx', True)
        accurate = kwargs.get('accurate', True)
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')

        baseX = kwargs['sw_lng'];
        baseY = kwargs['sw_lat'];
        distanceX = kwargs['ne_lng'];
        distanceY = kwargs['ne_lat'];
        pol_str = 'POLYGON(({0} {1},{0} {3},{2} {3},{2} {1},{0} {1}))'.format(baseX, baseY, distanceX \
                                                                                  ,distanceY)
        if not kwargs.get('show_markers', True):
            return MarkerResult(markers=db.session.query(AccidentMarker).filter(sql.false()), total_records=0)

        markers = db.session.query(AccidentMarker) \
            .filter(AccidentMarker.geom.intersects(pol_str)) \
            .filter(AccidentMarker.created >= kwargs['start_date']) \
            .filter(AccidentMarker.created < kwargs['end_date']) \
            .order_by(desc(AccidentMarker.created))

        if not kwargs['show_rsa']:
            markers = markers.filter(AccidentMarker.provider_code != CONST.RSA_PROVIDER_CODE)

        if not kwargs['show_accidents']:
            markers = markers.filter(and_(AccidentMarker.provider_code != CONST.CBS_ACCIDENT_TYPE_1_CODE,
                                          AccidentMarker.provider_code != CONST.CBS_ACCIDENT_TYPE_3_CODE,
                                          AccidentMarker.provider_code != CONST.UNITED_HATZALA_CODE))


        if yield_per:
            markers = markers.yield_per(yield_per)
        if accurate and not approx:
            markers = markers.filter(AccidentMarker.locationAccuracy == 1)
        elif approx and not accurate:
            markers = markers.filter(AccidentMarker.locationAccuracy != 1)
        elif not accurate and not approx:
            return MarkerResult(markers=db.session.query(AccidentMarker).filter(sql.false()), total_records=0)
        if not kwargs.get('show_fatal', True):
            markers = markers.filter(AccidentMarker.severity != 1)
        if not kwargs.get('show_severe', True):
            markers = markers.filter(AccidentMarker.severity != 2)
        if not kwargs.get('show_light', True):
            markers = markers.filter(AccidentMarker.severity != 3)
        if kwargs.get('show_urban', 3) != 3:
            if kwargs['show_urban'] == 2:
                markers = markers.filter(AccidentMarker.roadType >= 1).filter(AccidentMarker.roadType <= 2)
            elif kwargs['show_urban'] == 1:
                markers = markers.filter(AccidentMarker.roadType >= 3).filter(AccidentMarker.roadType <= 4)
            else:
                return MarkerResult(markers=db.session.query(AccidentMarker).filter(sql.false()), total_records=0)
        if kwargs.get('show_intersection', 3) != 3:
            if kwargs['show_intersection'] == 2:
                markers = markers.filter(AccidentMarker.roadType != 2).filter(AccidentMarker.roadType != 4)
            elif kwargs['show_intersection'] == 1:
                markers = markers.filter(AccidentMarker.roadType != 1).filter(AccidentMarker.roadType != 3)
            else:
                return MarkerResult(markers=db.session.query(AccidentMarker).filter(sql.false()), total_records=0)
        if kwargs.get('show_lane', 3) != 3:
            if kwargs['show_lane'] == 2:
                markers = markers.filter(AccidentMarker.one_lane >= 2).filter(AccidentMarker.one_lane <= 3)
            elif kwargs['show_lane'] == 1:
                markers = markers.filter(AccidentMarker.one_lane == 1)
            else:
                return MarkerResult(markers=db.session.query(AccidentMarker).filter(sql.false()), total_records=0)

        if kwargs.get('show_day', 7) != 7:
            markers = markers.filter(func.extract("dow", AccidentMarker.created) == kwargs['show_day'])
        if kwargs.get('show_holiday', 0) != 0:
            markers = markers.filter(AccidentMarker.dayType == kwargs['show_holiday'])

        if kwargs.get('show_time', 24) != 24:
            if kwargs['show_time'] == 25:     # Daylight (6-18)
                markers = markers.filter(func.extract("hour", AccidentMarker.created) >= 6)\
                                 .filter(func.extract("hour", AccidentMarker.created) < 18)
            elif kwargs['show_time'] == 26:   # Darktime (18-6)
                markers = markers.filter((func.extract("hour", AccidentMarker.created) >= 18) |
                                         (func.extract("hour", AccidentMarker.created) < 6))
            else:
                markers = markers.filter(func.extract("hour", AccidentMarker.created) >= kwargs['show_time'])\
                                 .filter(func.extract("hour", AccidentMarker.created) < kwargs['show_time']+6)
        elif kwargs['start_time'] != 25 and kwargs['end_time'] != 25:
            markers = markers.filter(func.extract("hour", AccidentMarker.created) >= kwargs['start_time'])\
                             .filter(func.extract("hour", AccidentMarker.created) < kwargs['end_time'])
        if kwargs.get('weather', 0) != 0:
            markers = markers.filter(AccidentMarker.weather == kwargs['weather'])
        if kwargs.get('road', 0) != 0:
            markers = markers.filter(AccidentMarker.roadShape == kwargs['road'])
        if kwargs.get('separation', 0) != 0:
            markers = markers.filter(AccidentMarker.multi_lane == kwargs['separation'])
        if kwargs.get('surface', 0) != 0:
            markers = markers.filter(AccidentMarker.road_surface == kwargs['surface'])
        if kwargs.get('acctype', 0) != 0:
            if kwargs['acctype'] <= 20:
                markers = markers.filter(AccidentMarker.subtype == kwargs['acctype'])
            elif kwargs['acctype'] == CONST.BIKE_ACCIDENTS:
                markers = markers.filter(AccidentMarker.vehicles.any(Vehicle.vehicle_type == CONST.VEHICLE_TYPE_BIKE))
        if kwargs.get('controlmeasure', 0) != 0:
            markers = markers.filter(AccidentMarker.road_control == kwargs['controlmeasure'])
        if kwargs.get('district', 0) != 0:
            markers = markers.filter(AccidentMarker.unit == kwargs['district'])

        if kwargs.get('case_type', 0) != 0:
            markers = markers.filter(AccidentMarker.provider_code == kwargs['case_type'])

        if is_thin:
            markers = markers.options(load_only("id", "longitude", "latitude"))

        if kwargs.get('age_groups'):
            markers = markers.filter(AccidentMarker.involved.any(Involved.age_group.in_(kwargs.get('age_groups').split(','))))

        total_records = markers.count()
        if page and per_page:
            markers = markers.offset((page - 1 ) * per_page).limit(per_page)

        if involved_and_vehicles:
            fetch_markers = kwargs.get('fetch_markers', True)
            fetch_vehicles = kwargs.get('fetch_vehicles', True)
            fetch_involved = kwargs.get('fetch_involved', True)
            markers_ids = [marker.id for marker in markers]
            markers = None
            vehicles = None
            involved = None
            if fetch_markers:
                markers = db.session.query(AccidentMarker).filter(AccidentMarker.id.in_(markers_ids))
            if fetch_vehicles:
                vehicles = db.session.query(Vehicle).filter(Vehicle.accident_id.in_(markers_ids))
            if fetch_involved:
                involved = db.session.query(Involved).filter(Involved.accident_id.in_(markers_ids))
            result = markers.all() if markers is not None else [], vehicles.all() if vehicles is not None else [], \
                   involved.all() if involved is not None else []
            return MarkerResult(markers=result, total_records=len(result))
        else:
            return MarkerResult(markers=markers, total_records=total_records)

    @staticmethod
    def get_marker(marker_id):
        return db.session.query(AccidentMarker).filter_by(id=marker_id)

    @classmethod
    def parse(cls, data):
        return AccidentMarker(
            type=CONST.MARKER_TYPE_ACCIDENT,
            title=data["title"],
            description=data["description"],
            latitude=data["latitude"],
            longitude=data["longitude"]
        )


class DiscussionMarker(MarkerMixin, Base):
    __tablename__ = "discussions"
    __table_args__ = (
        Index('disc_long_lat_idx', 'latitude', 'longitude'),
        Index('idx_discussions_geom', 'geom', unique=False)
    )

    __mapper_args__ = {
        'polymorphic_identity': CONST.MARKER_TYPE_DISCUSSION
    }

    identifier = Column(String(50), unique=True)
    geom = Column(Geometry('POINT'))

    def serialize(self, is_thin=False):
        return {
                "id": str(self.id),
                "latitude": self.latitude,
                "longitude": self.longitude,
                "created": self.created.isoformat(),
                "title": self.title,
                "identifier": self.identifier,
                "type": self.type
                }

    @staticmethod
    def get_by_identifier(identifier):
        return db.session.query(DiscussionMarker).filter_by(identifier=identifier)

    @classmethod
    def parse(cls, data):
        # FIXME the id should be generated automatically, but isn't
        last = db.session.query(DiscussionMarker).order_by('-id').first()
        return DiscussionMarker(
            id=last.id + 1 if last else 0,
            latitude=data["latitude"],
            longitude=data["longitude"],
            created=datetime.datetime.now(),
            title=data["title"],
            identifier=data["identifier"],
            type=CONST.MARKER_TYPE_DISCUSSION
        )

    @staticmethod
    def bounding_box_query(ne_lat, ne_lng, sw_lat, sw_lng, show_discussions):
        if not show_discussions:
            return db.session.query(AccidentMarker).filter(sql.false())
        markers = db.session.query(DiscussionMarker) \
            .filter(DiscussionMarker.longitude <= ne_lng) \
            .filter(DiscussionMarker.longitude >= sw_lng) \
            .filter(DiscussionMarker.latitude <= ne_lat) \
            .filter(DiscussionMarker.latitude >= sw_lat) \
            .order_by(desc(DiscussionMarker.created))
        return markers


class Involved(Base):
    __tablename__ = "involved"
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer())
    accident_id = Column(BigInteger())
    involved_type = Column(Integer())
    license_acquiring_date = Column(Integer())
    age_group = Column(Integer())
    sex = Column(Integer())
    car_type = Column(Integer())
    safety_measures = Column(Integer())
    involve_yishuv_symbol = Column(Integer())
    injury_severity = Column(Integer())
    injured_type = Column(Integer())
    injured_position = Column(Integer())
    population_type = Column(Integer())
    home_region = Column(Integer())
    home_district = Column(Integer())
    home_natural_area = Column(Integer())
    home_municipal_status = Column(Integer())
    home_residence_type = Column(Integer())
    hospital_time = Column(Integer())
    medical_type = Column(Integer())
    release_dest = Column(Integer())
    safety_measures_use = Column(Integer())
    late_deceased = Column(Integer())
    car_id = Column(Integer())
    involve_id = Column(Integer())
    accident_year = Column(Integer())
    accident_month = Column(Integer())
    __table_args__ = (ForeignKeyConstraint([accident_id, provider_code],
                                           [AccidentMarker.id, AccidentMarker.provider_code],
                                           ondelete="CASCADE"),
                      Index('accident_id_idx_involved', 'accident_id', unique=False),
                      Index('provider_and_id_idx_involved', 'provider_and_id', unique=False),
                      {})

    def serialize(self):
        return {
            "id": self.id,
            "provider_code": self.provider_code,
            "accident_id": self.accident_id,
            "involved_type": self.involved_type,
            "license_acquiring_date": self.license_acquiring_date,
            "age_group": self.age_group,
            "sex": self.sex,
            "car_type": self.car_type,
            "safety_measures": self.safety_measures,
            "involve_yishuv_symbol": self.involve_yishuv_symbol,
            "injury_severity": self.injury_severity,
            "injured_type": self.injured_type,
            "injured_position": self.injured_position,
            "population_type": self.population_type,
            "home_region": self.home_region,
            "home_district": self.home_district,
            "home_natural_area": self.home_natural_area,
            "home_municipal_status": self.home_municipal_status,
            "home_residence_type": self.home_residence_type,
            "hospital_time": self.hospital_time,
            "medical_type": self.medical_type,
            "release_dest": self.release_dest,
            "safety_measures_use": self.safety_measures_use,
            "late_deceased": self.late_deceased
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer(), primary_key=True)
    symbol_code = Column(Integer())
    name = Column(String())
    search_heb = Column(String())
    search_eng = Column(String())
    search_priority = Column(Integer())

    def serialize(self):
        return {
            "id": self.id,
            "symbol_code": self.symbol_code,
            "name": self.name,
            "search_heb": self.search_heb,
            "search_eng": self.search_eng,
            "search_priority": self.search_priority
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class RegisteredVehicle(Base):
    __tablename__ = "cities_vehicles_registered"
    id = Column(Integer(), primary_key=True)
    city_id = Column(Integer())
    year = Column(Integer())
    name = Column(String())
    name_eng = Column(String())
    search_name = Column(String())
    motorcycle = Column(Integer())
    special = Column(Integer())
    taxi = Column(Integer())
    bus = Column(Integer())
    minibus = Column(Integer())
    truck_over3500 = Column(Integer())
    truck_upto3500 = Column(Integer())
    private = Column(Integer())
    population_year = Column(Integer())
    population = Column(Integer())
    total = Column(Integer())

    def serialize(self):
        return {
            "id": self.id,
            "city_id": self.city_id,
            "year": self.year,
            "name": self.name,
            "name_eng": self.name_eng,
            "search_name": self.search_name,
            "motorcycle": self.motorcycle,
            "special": self.special,
            "taxi": self.taxi,
            "bus": self.bus,
            "minibus": self.minibus,
            "truck_over3500": self.truck_over3500,
            "truck_upto3500": self.truck_upto3500,
            "private": self.private,
            "population_year": self.population_year,
            "population": self.population,
            "total" : self.total
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer())
    accident_id = Column(BigInteger())
    engine_volume = Column(Integer())
    manufacturing_year = Column(Integer())
    driving_directions = Column(Integer())
    vehicle_status = Column(Integer())
    vehicle_attribution = Column(Integer())
    vehicle_type = Column(Integer())
    seats = Column(Integer())
    total_weight = Column(Integer())
    __table_args__ = (ForeignKeyConstraint([accident_id, provider_code],
                                           [AccidentMarker.id, AccidentMarker.provider_code],
                                           ondelete="CASCADE"),
                      Index('accident_id_idx_vehicles', 'accident_id', unique=False),
                      Index('provider_and_id_idx_vehicles', 'provider_and_id', unique=False),
                      {})

    def serialize(self):
        return {
            "id": self.id,
            "provider_code": self.provider_code,
            "accident_id": self.accident_id,
            "engine_volume": self.engine_volume,
            "manufacturing_year": self.manufacturing_year,
            "driving_directions": self.driving_directions,
            "vehicle_status": self.vehicle_status,
            "vehicle_attribution": self.vehicle_attribution,
            "vehicle_type": self.vehicle_type,
            "seats": self.seats,
            "total_weight": self.total_weight
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

class GeneralPreferences(Base):
    __tablename__ = "general_preferences"
    user_id = Column(Integer(), ForeignKey('users.id'), primary_key=True)
    minimum_displayed_severity = Column(Integer(), nullable=True)
    resource_type = Column(String(64), nullable=True)

    def serialize(self):
        return {
            "user_id": self.user_id,
            "minimum_displayed_severity": self.minimum_displayed_severity,
            "resource_type": self.resource_type
        }

class ReportPreferences(Base):
    __tablename__ = "report_preferences"
    user_id = Column(Integer(), ForeignKey('users.id'), primary_key=True)
    line_number = Column(Integer(), primary_key=True)
    historical_report = Column(Boolean(), default=False)
    how_many_months_back = Column(Integer(), nullable=True)
    latitude = Column(Float())
    longitude = Column(Float())
    radius = Column(Float())
    minimum_severity = Column(Integer())

    def serialize(self):
        return {
            "user_id": self.user_id,
            "line_number": self.line_number,
            "historical_report": self.historical_report,
            "how_many_months_back": self.how_many_months_back,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius": self.radius,
            "minimum_severity": self.minimum_severity
        }


class AccidentsNoLocation(Base, MarkerMixin):
    __tablename__ = "markers_no_location"
    __table_args__ = (
        Index('id_idx_markers_no_location', 'id', unique=False),
        Index('provider_and_id_idx_markers_no_location', 'provider_and_id', unique=True),
    )
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer(), primary_key=True)
    description = Column(Text())
    subtype = Column(Integer())
    severity = Column(Integer())
    address = Column(Text())
    locationAccuracy = Column(Integer())
    roadType = Column(Integer())
    roadShape = Column(Integer())
    dayType = Column(Integer())
    unit = Column(Integer())
    mainStreet = Column(Text())
    secondaryStreet = Column(Text())
    junction = Column(Text())
    one_lane = Column(Integer())
    multi_lane = Column(Integer())
    speed_limit = Column(Integer())
    intactness = Column(Integer())
    road_width = Column(Integer())
    road_sign = Column(Integer())
    road_light = Column(Integer())
    road_control = Column(Integer())
    weather = Column(Integer())
    road_surface = Column(Integer())
    road_object = Column(Integer())
    object_distance = Column(Integer())
    didnt_cross = Column(Integer())
    cross_mode = Column(Integer())
    cross_location = Column(Integer())
    cross_direction = Column(Integer())
    involved = relationship("InvolvedNoLocation", foreign_keys="InvolvedNoLocation.accident_id")
    vehicles = relationship("VehicleNoLocation", foreign_keys="VehicleNoLocation.accident_id")
    video_link = Column(Text())
    road1 = Column(Integer())
    road2 = Column(Integer())
    km = Column(Float)
    yishuv_symbol = Column(Integer())
    geo_area = Column(Integer())
    day_night = Column(Integer())
    day_in_week = Column(Integer())
    traffic_light = Column(Integer())
    region = Column(Integer())
    district = Column(Integer())
    natural_area = Column(Integer())
    minizipali_status = Column(Integer())
    yishuv_shape = Column(Integer())
    street1 = Column(Integer())
    street2 = Column(Integer())
    home = Column(Integer())
    urban_intersection = Column(Integer())
    non_urban_intersection = Column(Integer())
    accident_year = Column(Integer())
    accident_month = Column(Integer())
    accident_day = Column(Integer())
    accident_hour_raw = Column(Integer())
    accident_hour = Column(Integer())
    accident_minute = Column(Integer())

class InvolvedNoLocation(Base):
    __tablename__ = "involved_no_location"
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer())
    accident_id = Column(BigInteger())
    involved_type = Column(Integer())
    license_acquiring_date = Column(Integer())
    age_group = Column(Integer())
    sex = Column(Integer())
    car_type = Column(Integer())
    safety_measures = Column(Integer())
    involve_yishuv_symbol = Column(Integer())
    injury_severity = Column(Integer())
    injured_type = Column(Integer())
    injured_position = Column(Integer())
    population_type = Column(Integer())
    home_region = Column(Integer())
    home_district = Column(Integer())
    home_natural_area = Column(Integer())
    home_municipal_status = Column(Integer())
    home_residence_type = Column(Integer())
    hospital_time = Column(Integer())
    medical_type = Column(Integer())
    release_dest = Column(Integer())
    safety_measures_use = Column(Integer())
    late_deceased = Column(Integer())
    car_id = Column(Integer())
    involve_id = Column(Integer())
    accident_year = Column(Integer())
    accident_month = Column(Integer())
    __table_args__ = (ForeignKeyConstraint([accident_id, provider_code],
                                           [AccidentsNoLocation.id, AccidentsNoLocation.provider_code],
                                           ondelete="CASCADE"),
                      Index('accident_id_idx_involved_no_location', 'accident_id'),
                      Index('provider_and_id_idx_involved_no_location', 'provider_and_id', unique=False),
                      {})
class VehicleNoLocation(Base):
    __tablename__ = "vehicles_no_location"
    id = Column(BigInteger(), primary_key=True)
    provider_and_id = Column(BigInteger())
    provider_code = Column(Integer())
    accident_id = Column(BigInteger())
    engine_volume = Column(Integer())
    manufacturing_year = Column(Integer())
    driving_directions = Column(Integer())
    vehicle_status = Column(Integer())
    vehicle_attribution = Column(Integer())
    vehicle_type = Column(Integer())
    seats = Column(Integer())
    total_weight = Column(Integer())
    __table_args__ = (ForeignKeyConstraint([accident_id, provider_code],
                                           [AccidentsNoLocation.id, AccidentsNoLocation.provider_code],
                                           ondelete="CASCADE"),
                      Index('accident_id_idx_vehicles_no_location', 'accident_id'),
                      Index('provider_and_id_idx_vehicles_no_location', 'provider_and_id', unique=False),
                      {})


class School(Base):
    __tablename__ = "schools"
    id = Column(BigInteger(), primary_key=True, index=True)
    fcode_type = Column(Integer(), nullable=True)
    yishuv_symbol = Column(Integer(), nullable=True, index=True)
    yishuv_name = Column(Text(), nullable=True)
    school_name = Column(Text(), nullable=True)
    school_latin_name = Column(Text(), nullable=True)
    usg = Column(Integer(), nullable=True)
    usg_code = Column(Integer(), nullable=True)
    e_ord = Column(Float(), nullable=True)
    n_ord = Column(Float(), nullable=True)
    longitude = Column(Float(), nullable=True)
    latitude = Column(Float(), nullable=True)
    geom = Column(Geometry('POINT', srid=4326), index=True)
    data_year = Column(Integer(), nullable=True)
    prdct_ver = Column(DateTime, default=None)
    x = Column(Float(), nullable=True)
    y = Column(Float(), nullable=True)
