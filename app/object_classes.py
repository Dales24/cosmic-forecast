"""Object categories for telescope patch classification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectClass:
    name: str
    slug: str
    group: str


NATURAL_OBJECTS = (
    ObjectClass("Asteroid", "asteroid", "natural"),
    ObjectClass("Comet", "comet", "natural"),
    ObjectClass("Meteor", "meteor", "natural"),
    ObjectClass("Meteoroid", "meteoroid", "natural"),
    ObjectClass("Near-Earth Object", "near_earth_object", "natural"),
)

ARTIFICIAL_OBJECTS = (
    ObjectClass("Satellite", "satellite", "artificial"),
    ObjectClass("Space Debris", "space_debris", "artificial"),
    ObjectClass("Rocket Body", "rocket_body", "artificial"),
    ObjectClass("International Space Station", "iss", "artificial"),
)

DEEP_SPACE_OBJECTS = (
    ObjectClass("Galaxy", "galaxy", "deep_space"),
    ObjectClass("Nebula", "nebula", "deep_space"),
    ObjectClass("Star Cluster", "star_cluster", "deep_space"),
    ObjectClass("Variable Star", "variable_star", "deep_space"),
    ObjectClass("Star", "star", "deep_space"),
    ObjectClass("Black Hole", "black_hole", "deep_space"),
    ObjectClass("Quasar", "quasar", "deep_space"),
    ObjectClass("Pulsar", "pulsar", "deep_space"),
    ObjectClass("Supernova Remnant", "supernova_remnant", "deep_space"),
)

# Solar-system bodies rendered as their own scene objects (Sun, Earth, Moon,
# and the planets), so each is a first-class classification target too.
SOLAR_SYSTEM_OBJECTS = (
    ObjectClass("Planet", "planet", "solar_system"),
    ObjectClass("Sun", "sun", "solar_system"),
    ObjectClass("Moon", "moon", "solar_system"),
    ObjectClass("Earth", "earth", "solar_system"),
)

UNKNOWN_OBJECTS = (ObjectClass("Unidentified", "ufo", "unknown"),)

OBJECT_CLASSES = (
    NATURAL_OBJECTS
    + ARTIFICIAL_OBJECTS
    + DEEP_SPACE_OBJECTS
    + SOLAR_SYSTEM_OBJECTS
    + UNKNOWN_OBJECTS
)
NUM_CLASSES = len(OBJECT_CLASSES)
CLASS_NAMES = [obj.name for obj in OBJECT_CLASSES]
CLASS_SLUGS = [obj.slug for obj in OBJECT_CLASSES]
CLASS_GROUPS = [obj.group for obj in OBJECT_CLASSES]
SLUG_TO_INDEX = {obj.slug: index for index, obj in enumerate(OBJECT_CLASSES)}
INDEX_TO_CLASS = {index: obj for index, obj in enumerate(OBJECT_CLASSES)}
