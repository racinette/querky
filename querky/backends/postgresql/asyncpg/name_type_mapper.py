from querky.backends.postgresql.name_type_mapper import PostgresqlNameTypeMapper

from querky.base_types import TypeMetaData
from querky.common_imports import DATETIME_MODULE
from querky.common_imports import DECIMAL as DECIMAL_IMPORT
from querky.common_imports import UUID as UUID_IMPORT
from querky.common_imports import UNION as UNION_IMPORT


ASYNCPG_RANGE_IMPORT = "from asyncpg import Range as _Range"
ASYNCPG_RECORD_IMPORT = "from asyncpg import Record as _Record"
ASYNCPG_BITSTRING_IMPORT = "from asyncpg import BitString as _BitString"
ASYNCPG_BOX_IMPORT = "from asyncpg import Box as _Box"
ASYNCPG_CIRCLE_IMPORT = "from asyncpg import Circle as _Circle"
ASYNCPG_LINE_IMPORT = "from asyncpg import Line as _Line"
ASYNCPG_LINE_SEGMENT_IMPORT = "from asyncpg import LineSegment as _LineSegment"
ASYNCPG_PATH_IMPORT = "from asyncpg import Path as _Path"
ASYNCPG_POINT_IMPORT = "from asyncpg import Point as _Point"
ASYNCPG_POLYGON_IMPORT = "from asyncpg import Polygon as _Polygon"


INT = TypeMetaData("int")
FLOAT = TypeMetaData("float")
DECIMAL = TypeMetaData("Decimal", {DECIMAL_IMPORT})
STRING = TypeMetaData("str")
BOOL = TypeMetaData("bool")
TIMESTAMP = TypeMetaData("datetime.datetime", {DATETIME_MODULE})
TIMEDELTA = TypeMetaData("datetime.timedelta", {DATETIME_MODULE})
TIME = TypeMetaData("datetime.time", {DATETIME_MODULE})
INET = TypeMetaData("Union[IPv4Interface, IPv6Interface, IPv4Address, IPv6Address]", {
    UNION_IMPORT,
    "from ipaddress import IPv4Interface, IPv6Interface, IPv4Address, IPv6Address"
})
CIDR = TypeMetaData("Union[IPv4Network, IPv6Network]", {
    UNION_IMPORT,
    "from ipaddress import IPv4Network, IPv6Network"
})

NONE = TypeMetaData("None")
UUID = TypeMetaData("UUID", {UUID_IMPORT})

NUMRANGE = TypeMetaData("_Range", {ASYNCPG_RANGE_IMPORT})
TSRANGE = TypeMetaData("_Range", {ASYNCPG_RANGE_IMPORT})
INT8RANGE = TypeMetaData("_Range", {ASYNCPG_RANGE_IMPORT})
INT4RANGE = TypeMetaData("_Range", {ASYNCPG_RANGE_IMPORT})

NUMMULTIRANGE = TypeMetaData("list[_Range]", {ASYNCPG_RANGE_IMPORT})
TSMULTIRANGE = TypeMetaData("list[_Range]", {ASYNCPG_RANGE_IMPORT})
INT4MULTIRANGE = TypeMetaData("list[_Range]", {ASYNCPG_RANGE_IMPORT})
INT8MULTIRANGE = TypeMetaData("list[_Range]", {ASYNCPG_RANGE_IMPORT})

RECORD = TypeMetaData("_Record", {ASYNCPG_RECORD_IMPORT})

BITSTRING = TypeMetaData("_BitString", {ASYNCPG_BITSTRING_IMPORT})

BOX = TypeMetaData("_Box", {ASYNCPG_BOX_IMPORT})
BYTEA = TypeMetaData("bytes")

CIRCLE = TypeMetaData("_Circle", {ASYNCPG_CIRCLE_IMPORT})

DATE = TypeMetaData("datetime.date", {DATETIME_MODULE})

LINE = TypeMetaData("_Line", {ASYNCPG_LINE_IMPORT})
LINE_SEGMENT = TypeMetaData("_LineSegment", {ASYNCPG_LINE_SEGMENT_IMPORT})

PATH = TypeMetaData("_Path", {ASYNCPG_PATH_IMPORT})
POINT = TypeMetaData("_Point", {ASYNCPG_POINT_IMPORT})

POLYGON = TypeMetaData("_Polygon", {ASYNCPG_POLYGON_IMPORT})
TID = TypeMetaData("tuple")


DEFAULT_TYPEMAP = {
    "pg_catalog": {
        "int8": INT,
        "bigint": INT,
        "int4": INT,
        "integer": INT,
        "int2": INT,
        "smallint": INT,

        "float4": FLOAT,
        "float8": FLOAT,
        "double precision": FLOAT,

        "numeric": DECIMAL,

        "char": STRING,
        "varchar": STRING,
        "character varying": STRING,
        "text": STRING,
        "jsonb": STRING,
        "json": STRING,
        "bpchar": STRING,

        "bool": BOOL,
        "boolean": BOOL,

        "timestamp": TIMESTAMP,
        "timestamptz": TIMESTAMP,
        "timestamp with time zone": TIMESTAMP,
        'interval': TIMEDELTA,
        "time without time zone": TIME,
        "time with time zone": TIME,

        'void': NONE,

        'uuid': UUID,

        "inet": INET,

        "numrange": NUMRANGE,
        "int8range": INT8RANGE,
        "int4range": INT4RANGE,
        "tsrange": TSRANGE,

        "nummultirange": NUMMULTIRANGE,
        "tsmultirange": TSMULTIRANGE,
        "int4multirange": INT4MULTIRANGE,
        "int8multirange": INT8MULTIRANGE,

        "record": RECORD,

        "bitstring": BITSTRING,
        "varbit": BITSTRING,
        "bit varying": BITSTRING,

        "box": BOX,

        "bytea": BYTEA,

        "cidr": CIDR,

        "macaddr": STRING,

        "circle": CIRCLE,
        "date": DATE,

        "line": LINE,
        "lseg": LINE_SEGMENT,
        "money": STRING,

        "path": PATH,
        "point": POINT,
        "polygon": POLYGON,

        "tid": TID

    },
}


class AsyncpgNameTypeMapper(PostgresqlNameTypeMapper):
    def __init__(self, typemap: dict[str, dict[str, TypeMetaData]] | None = None):
        if typemap is None:
            typemap = DEFAULT_TYPEMAP
        super().__init__(typemap)
