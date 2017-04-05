# EMACS settings: -*-	tab-width: 2; indent-tabs-mode: t; python-indent-offset: 2 -*-
# vim: tabstop=2:shiftwidth=2:noexpandtab
# kate: tab-width 2; replace-tabs off; indent-width 2;
# ==============================================================================
# Authors:            Patrick Lehmann
#
# Python procedures:   A streaming VHDL parser
#
# Description:
# ------------------------------------
#		TODO:
#
# License:
# ==============================================================================
# Copyright 2007-2017 Patrick Lehmann - Dresden, Germany
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
#
# load dependencies
from collections                          import ChainMap
from itertools                            import chain

from pyVHDLParser.Blocks                  import CommentBlock, EndOfDocumentBlock
from pyVHDLParser.Blocks.Common           import LinebreakBlock, IndentationBlock
from pyVHDLParser.Blocks.List             import GenericList, ParameterList
from pyVHDLParser.Blocks.Object.Constant  import ConstantBlock
from pyVHDLParser.Blocks.Object.Variable  import VariableBlock
from pyVHDLParser.Blocks.Reference        import Use
from pyVHDLParser.Blocks.Reporting.Report import ReportBlock
from pyVHDLParser.Blocks.Sequential       import Procedure
from pyVHDLParser.Groups                  import ParserState, Group, BlockParserException, EndOfDocumentGroup
from pyVHDLParser.Groups.Comment          import WhitespaceGroup, CommentGroup
from pyVHDLParser.Groups.List             import GenericListGroup, ParameterListGroup
from pyVHDLParser.Groups.Object           import ConstantGroup, VariableGroup
from pyVHDLParser.Groups.Reference        import UseGroup


class ProcedureGroup(Group):
	DECLARATION_SIMPLE_BLOCKS = {
		Use.StartBlock:  UseGroup,
		ConstantBlock:   ConstantGroup,
		VariableBlock:   VariableGroup
	}
	DECLARATION_COMPOUND_BLOCKS = {
		# Procedure.NameBlock:       ProcedureGroup,
		# Procedure.NameBlock:      ProcedureGroup
	}
	STATEMENT_SIMPLE_BLOCKS = {
		# ReportBlock:              ReportGroup
	}
	STATEMENT_COMPOUND_BLOCKS = {
		# If.OpenBlock:        IfGroup
	}

	def __init__(self, previousGroup, startBlock, endBlock=None):
		super().__init__(previousGroup, startBlock, endBlock)

		self._subGroups = dict(ChainMap(
			{v: [] for v in chain(
				self.DECLARATION_SIMPLE_BLOCKS.values(),
				self.DECLARATION_COMPOUND_BLOCKS.values(),
				self.STATEMENT_SIMPLE_BLOCKS.values(),
				self.STATEMENT_COMPOUND_BLOCKS.values()
			)},
			{CommentGroup: [],
			 WhitespaceGroup: []
			 }
		))

	@classmethod
	def stateParse(cls, parserState: ParserState):
		currentBlock = parserState.Block

		# consume OpenBlock
		if isinstance(currentBlock, Procedure.NameBlock):
			parserState.NextGroup =   cls(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.NextState =   cls.stateParseGenerics
			return
		else:
			raise BlockParserException("Begin of procedure expected.", currentBlock)

	@classmethod
	def stateParseGenerics(cls, parserState: ParserState):
		currentBlock = parserState.Block

		if isinstance(currentBlock, GenericList.OpenBlock):
			parserState.NextState =   cls.stateParseParameters
			parserState.PushState =   GenericListGroup.stateParse
			parserState.NextGroup =   GenericListGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, ParameterList.OpenBlock):
			parserState.NextState =   cls.stateParseDeclarations
			parserState.PushState =   ParameterListGroup.stateParse
			parserState.NextGroup =   ParameterListGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, (LinebreakBlock, IndentationBlock)):
			parserState.PushState =   WhitespaceGroup.stateParse
			parserState.NextGroup =   WhitespaceGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, CommentBlock):
			parserState.PushState =   CommentGroup.stateParse
			parserState.NextGroup =   CommentGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return

		if isinstance(currentBlock, EndOfDocumentBlock):
			parserState.NextGroup = EndOfDocumentGroup(currentBlock)
			return

		raise BlockParserException("End of generic clause not found.", currentBlock)


	@classmethod
	def stateParseParameters(cls, parserState: ParserState):
		currentBlock = parserState.Block

		if isinstance(currentBlock, GenericList.OpenBlock):
			parserState.NextState =   cls.stateParseDeclarations
			parserState.PushState =   ParameterListGroup.stateParse
			parserState.NextGroup =   ParameterListGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, (LinebreakBlock, IndentationBlock)):
			parserState.PushState =   WhitespaceGroup.stateParse
			parserState.NextGroup =   WhitespaceGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, CommentBlock):
			parserState.PushState =   CommentGroup.stateParse
			parserState.NextGroup =   CommentGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return

		if isinstance(currentBlock, EndOfDocumentBlock):
			parserState.NextGroup = EndOfDocumentGroup(currentBlock)
			return

		raise BlockParserException("End of parameters not found.", currentBlock)

	@classmethod
	def stateParseDeclarations(cls, parserState: ParserState):
		currentBlock = parserState.Block

		if isinstance(currentBlock, Procedure.BeginBlock):
			parserState.NextState =   cls.stateParseStatements
			return
		elif isinstance(currentBlock, Procedure.EndBlock):
			parserState.NextGroup =   cls(parserState.LastGroup, parserState.BlockMarker, parserState.Block)
			parserState.Pop()
			parserState.BlockMarker = None
			return
		elif isinstance(currentBlock, (LinebreakBlock, IndentationBlock)):
			parserState.PushState =   WhitespaceGroup.stateParse
			parserState.NextGroup =   WhitespaceGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, CommentBlock):
			parserState.PushState =   CommentGroup.stateParse
			parserState.NextGroup =   CommentGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		else:
			for block in cls.DECLARATION_SIMPLE_BLOCKS:
				if isinstance(currentBlock, block):
					group = cls.DECLARATION_SIMPLE_BLOCKS[block]
					parserState.PushState =   group.stateParse
					parserState.BlockMarker = currentBlock
					parserState.ReIssue =     True
					return

			for block in cls.DECLARATION_COMPOUND_BLOCKS:
				if isinstance(currentBlock, block):
					group =                   cls.DECLARATION_COMPOUND_BLOCKS[block]
					parserState.PushState =   group.stateParse
					parserState.BlockMarker = currentBlock
					parserState.ReIssue =     True
					return

		if isinstance(currentBlock, EndOfDocumentBlock):
			parserState.NextGroup = EndOfDocumentGroup(currentBlock)
			return

		raise BlockParserException("End of procedure declarative region not found.", currentBlock)

	@classmethod
	def stateParseStatements(cls, parserState: ParserState):
		currentBlock = parserState.Block

		if isinstance(currentBlock, Procedure.EndBlock):
			parserState.NextGroup =   cls(parserState.LastGroup, parserState.BlockMarker, parserState.Block)
			parserState.Pop()
			parserState.BlockMarker = None
			return
		elif isinstance(currentBlock, (LinebreakBlock, IndentationBlock)):
			parserState.PushState =   WhitespaceGroup.stateParse
			parserState.NextGroup =   WhitespaceGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		elif isinstance(currentBlock, CommentBlock):
			parserState.PushState =   CommentGroup.stateParse
			parserState.NextGroup =   CommentGroup(parserState.LastGroup, currentBlock)
			parserState.BlockMarker = currentBlock
			parserState.ReIssue =     True
			return
		else:
			for block in cls.STATEMENT_SIMPLE_BLOCKS:
				if isinstance(currentBlock, block):
					group = cls.STATEMENT_SIMPLE_BLOCKS[block]
					parserState.PushState =   group.stateParse
					parserState.BlockMarker = currentBlock
					parserState.ReIssue =     True
					return

			for block in cls.STATEMENT_COMPOUND_BLOCKS:
				if isinstance(currentBlock, block):
					group =                   cls.STATEMENT_COMPOUND_BLOCKS[block]
					parserState.PushState =   group.stateParse
					parserState.BlockMarker = currentBlock
					parserState.ReIssue =     True
					return

		if isinstance(currentBlock, EndOfDocumentBlock):
			parserState.NextGroup = EndOfDocumentGroup(currentBlock)
			return

		raise BlockParserException("End of procedure declaration not found.", currentBlock)
