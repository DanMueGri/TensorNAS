from enum import Enum, auto

from TensorNAS.Core.Layer import NetworkLayer


class Args(Enum):
    LAYERS = auto()


class Layer(NetworkLayer):
    def _gen_args(cls, input_shape, args):
        assert args
        return {cls.get_args_enum().LAYERS: args}

    def get_output_shape(self):
        return self.inputshape.get()

    def get_keras_layer(self, input_tensor):
        import tensorflow as tf

        return tf.keras.layers.Add(self.args.get(self.get_args_enum().LAYERS))(
            input_tensor
        )
