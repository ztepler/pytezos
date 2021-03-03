from typing import List
from typing import Tuple
from typing import Union
from typing import cast

from pytezos.context.abstract import AbstractContext
from pytezos.michelson.instructions.base import MichelsonInstruction
from pytezos.michelson.instructions.base import dispatch_types
from pytezos.michelson.instructions.base import format_stdout
from pytezos.michelson.stack import MichelsonStack
from pytezos.michelson.types import BytesType
from pytezos.michelson.types import ListType
from pytezos.michelson.types import MapType
from pytezos.michelson.types import NatType
from pytezos.michelson.types import NeverType
from pytezos.michelson.types import OptionType
from pytezos.michelson.types import SetType
from pytezos.michelson.types import StringType
from pytezos.michelson.types import UnitType


class ConcatInstruction(MichelsonInstruction, prim='CONCAT'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        a = cast(Union[StringType, BytesType, ListType], stack.pop1())
        a.assert_type_in(StringType, BytesType, ListType)
        if isinstance(a, ListType):
            a.assert_type_in(ListType)
            res_type, convert, delim = dispatch_types(a.args[0], mapping={
                (StringType,): (StringType, str, ''),
                (BytesType,): (BytesType, bytes, b'')
            })
            res = res_type.from_value(delim.join(map(convert, a)))
            stdout.append(format_stdout(cls.prim, [a], [res]))
        else:
            b = cast(Union[StringType, BytesType], stack.pop1())
            res_type, convert = dispatch_types(type(a), type(b), mapping={
                (StringType, StringType): (StringType, str),
                (BytesType, BytesType): (BytesType, bytes)
            })
            res = res_type.from_value(convert(a) + convert(b))
            stdout.append(format_stdout(cls.prim, [a, b], [res]))
        stack.push(res)
        return cls()


class PackInstruction(MichelsonInstruction, prim='PACK'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        a = stack.pop1()
        res = BytesType.from_value(a.pack())
        stack.push(res)
        stdout.append(format_stdout(cls.prim, [a], [res]))
        return cls()


class UnpackInstruction(MichelsonInstruction, prim='UNPACK', args_len=1):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        a = cast(BytesType, stack.pop1())
        a.assert_type_equal(BytesType)
        try:
            some = cls.args[0].unpack(bytes(a))
            res = OptionType.from_some(some)
        except Exception as e:
            stdout.append(f'{cls.prim}: {e}')
            res = OptionType.none(cls.args[0])
        stack.push(res)
        stdout.append(format_stdout(cls.prim, [a], [res]))
        return cls()


class SizeInstruction(MichelsonInstruction, prim='SIZE'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        src = cast(Union[StringType, BytesType, ListType, SetType, MapType], stack.pop1())
        src.assert_type_in(StringType, BytesType, ListType, SetType, MapType)
        res = NatType.from_value(len(src))
        stack.push(res)
        stdout.append(format_stdout(cls.prim, [src], [res]))
        return cls()


class SliceInstruction(MichelsonInstruction, prim='SLICE'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        offset, length, s = cast(Tuple[NatType, NatType, Union[StringType, BytesType]], stack.pop3())
        offset.assert_type_equal(NatType)
        length.assert_type_equal(NatType)
        s.assert_type_in(StringType, BytesType)
        start, stop = int(offset), int(offset) + int(length)
        if 0 <= start <= stop <= len(s):
            res = OptionType.from_some(s[start:stop])
        else:
            res = OptionType.none(type(s))
        stack.push(res)
        stdout.append(format_stdout(cls.prim, [offset, length, s], [res]))
        return cls()


class UnitInstruction(MichelsonInstruction, prim='UNIT'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        res = UnitType()
        stack.push(res)
        stdout.append(format_stdout(cls.prim, [], [res]))
        return cls()


class NeverInstruction(MichelsonInstruction, prim='NEVER'):

    @classmethod
    def execute(cls, stack: MichelsonStack, stdout: List[str], context: AbstractContext):
        never = cast(NeverType, stack.pop1())
        never.assert_type_equal(NeverType)
        stdout.append(format_stdout(cls.prim, [never], []))
        return cls()
