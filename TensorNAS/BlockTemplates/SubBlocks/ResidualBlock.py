from enum import Enum, auto
from tensorflow import keras

from TensorNAS.Core.ModelUtil import shortcut
from TensorNAS.Core.Block import Block
from TensorNAS.BlockTemplates.SubBlocks.FeatureExtractionBlock import (
    Block as FeatureExtractionBlock,
)


class SubBlockTypes(Enum):
    SAME_CONV2D = auto()


class Block(Block):
    MAX_SUB_BLOCKS = 1
    SUB_BLOCK_TYPES = SubBlockTypes

    def generate_random_sub_block(self, input_shape, layer_type):
        if layer_type == self.SUB_BLOCK_TYPES.SAME_CONV2D:
            return [
                FeatureExtractionBlock(
                    input_shape=input_shape, parent_block=self, layer_type=layer_type
                )
            ]
        return []

    def get_keras_layers(self, input_tensor):
        tmp = input_tensor
        for sb in self.input_blocks + self.middle_blocks + self.output_blocks:
            tmp = sb.get_keras_layers(tmp)
        return shortcut(input_tensor, tmp)
