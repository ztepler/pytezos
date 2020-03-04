from unittest import TestCase

from tests import abspath

from pytezos.repl.interpreter import Interpreter
from pytezos.michelson.converter import michelson_to_micheline
from pytezos.repl.parser import parse_expression


class OpcodeTestconcat_hello_bytes_88(TestCase):

    def setUp(self):
        self.maxDiff = None
        self.i = Interpreter(debug=True)
        
    def test_opcode_concat_hello_bytes_88(self):
        res = self.i.execute(f'INCLUDE "{abspath("opcodes/contracts/concat_hello_bytes.tz")}"')
        self.assertTrue(res['success'])
        
        res = self.i.execute('RUN { 0xab ; 0xcd } {}')
        self.assertTrue(res['success'])
        
        expected_expr = michelson_to_micheline('{ 0xffab ; 0xffcd }')
        expected_val = parse_expression(expected_expr, res['result'][1].type_expr)
        self.assertEqual(expected_val, res['result'][1]._val)