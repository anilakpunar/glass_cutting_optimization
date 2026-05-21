from enum import Enum


class GlassType(str, Enum):
    """Sektorde yaygin cam tipleri."""

    FLOAT = "float"
    TEMPERED = "tempered"          # temperli
    LAMINATED = "laminated"        # lamine
    LOW_E = "low_e"
    REFLECTIVE = "reflective"
    PATTERNED = "patterned"        # desenli
    MIRROR = "mirror"              # ayna


class CutOrientation(str, Enum):
    """Plaka uzerindeki yerlesim yonu."""

    NORMAL = "normal"
    ROTATED_90 = "rotated_90"


class GrainConstraint(str, Enum):
    """Desenli / kaplamali camlarda yon kisitlamasi.

    - NONE         : istenen yonde donmesi serbest
    - FIXED        : 90 derece donmesi yasak (desen yonu sabit)
    - PREFER_FIXED : mumkunse don dur me; gerekirse don
    """

    NONE = "none"
    FIXED = "fixed"
    PREFER_FIXED = "prefer_fixed"
