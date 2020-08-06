import tensorflow as tf
import keras
from tensorflowlayerargs import *
import numpy as np
import random
from nasmutator import *


class TensorNASModel:
    def __init__(
        self,
        layer_iterator,
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
        verbose=False,
    ):
        self.optimizer = optimizer
        self.loss = loss
        self.metrics = metrics
        self.layers = []
        self.verbose = verbose
        self.accuracy = None
        self.param_count = None

        # Here we pull our ModelLayer objects from the iterator containing our architecture
        for layer in layer_iterator:
            self._addlayer(layer.name, layer.args)

    def print(self):
        for layer in self.layers:
            layer.print()

    def loadlayersfromjson(self, json):
        if json:
            for x in range(len(json.keys())):
                layer = json.get(str(x))
                name = layer.get("name")
                args = layer.get("args")
                self.addlayer(name, args)

    def _addlayer(self, name, args):
        if name == "Conv2D":
            filters = args.get(Conv2DArgs.FILTERS.name, 1)
            kernel_size = tuple(args.get(Conv2DArgs.KERNEL_SIZE.name, (3, 3)))
            strides = args.get(Conv2DArgs.STRIDES.name, (1, 1))
            input_size = tuple(args.get(Conv2DArgs.INPUT_SIZE.name))
            activation = args.get(Conv2DArgs.ACTIVATION.name, Activations.RELU.value)
            dilation_rate = args.get(Conv2DArgs.DILATION_RATE.name, (1, 1))
            padding = args.get(Conv2DArgs.PADDING.name, PaddingArgs.SAME.value)
            self.layers.append(
                Conv2DLayer(
                    filters=filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    input_size=input_size,
                    activation=activation,
                    dilation_rate=dilation_rate,
                    padding=padding,
                )
            )
            if self.verbose:
                print(
                    "Created {} layer with {} filters, {} kernel size, {} stride size and {} input size".format(
                        name, filters, kernel_size, strides, input_size
                    )
                )
        elif name == "MaxPool2D" or name == "MaxPool3D":
            pool_size = tuple(args.get(MaxPool2DArgs.POOL_SIZE.name, (1, 1)))
            strides = args.get(MaxPool2DArgs.STRIDES.name, None)
            if name == "MaxPool2D":
                self.layers.append(MaxPool2DLayer(pool_size, strides))
                if self.verbose:
                    print(
                        "Created {} layer with {} pool size and {} stride size".format(
                            name, pool_size, strides
                        )
                    )
            else:
                self.layers.append(MaxPool3DLayer(pool_size, strides))
                if self.verbose:
                    print(
                        "Created {} layer with {} pool size and {} stride size".format(
                            name, pool_size, strides
                        )
                    )
        elif name == "Reshape":
            target_shape = args.get(ReshapeArgs.TARGET_SHAPE.name)
            self.layers.append(ReshapeLayer(target_shape))
            if self.verbose:
                print(
                    " Created {} layer with {} target shape".format(name, target_shape)
                )
        elif name == "Dense":
            units = args.get(DenseArgs.UNITS.name)
            activation = getattr(tf.nn, args.get(DenseArgs.ACTIVATION.name))
            self.layers.append(DenseLayer(units, activation))
            if self.verbose:
                print(
                    "Created {} layer with {} units and {} activation".format(
                        name, units, activation
                    )
                )
        elif name == "Flatten":
            self.layers.append(FlattenLayer())
            if self.verbose:
                print("Create {} layer".format(name))
        elif name == "Dropout":
            rate = args.get(DropoutArgs.RATE.name)
            self.layers.append(Dropout(rate))
            if self.verbose:
                print("Created {} layers with {} rate".format(name, rate))

    def _gettfmodel(self):
        model = keras.Sequential()
        for layer in self.layers:
            model.add(layer.getkeraslayer())
        model.compile(optimizer=self.optimizer, loss=self.loss, metrics=self.metrics)
        if self.verbose:
            model.summary()
        return model

    def evaluate(
        self, train_data, train_labels, test_data, test_labels, epochs, batch_size
    ):
        model = self._gettfmodel()
        model.fit(x=train_data, y=train_labels, epochs=epochs, batch_size=batch_size)
        self.param_count = int(
            np.sum([keras.backend.count_params(p) for p in model.trainable_weights])
        ) + int(
            np.sum([keras.backend.count_params(p) for p in model.non_trainable_weights])
        )
        self.accuracy = model.evaluate(test_data, test_labels)[1] * 100

        return self.param_count, self.accuracy


class ModelLayer:
    "Common layer properties"

    def __init__(self, name, args=None):
        self.name = name
        if args:
            self.args = args
        else:
            self.args = {}

    def getname(self):
        return self.name

    def getargs(self):
        return self.args

    def print(self):
        print("{} ->".format(self.name))
        for param_name, param_value in self.args.items():
            print("{}: {}".format(param_name, param_value))


class Conv2DLayer(ModelLayer):
    MUTATABLE_PARAMETERS = 6
    MAX_FILTER_COUNT = 128
    MAX_KERNEL_DIMENSION = 7
    MAX_STRIDE = 7
    MAX_DILATION = 5

    def __init__(
        self,
        filters,
        kernel_size,
        strides,
        input_size,
        padding=PaddingArgs.SAME.value,
        dilation_rate=(0, 0),
        activation=Activations.RELU.value,
    ):
        super().__init__("Conv2D")

        self.args[Conv2DArgs.FILTERS.name] = filters
        self.args[Conv2DArgs.KERNEL_SIZE.name] = kernel_size
        self.args[Conv2DArgs.STRIDES.name] = strides
        self.args[Conv2DArgs.INPUT_SIZE.name] = input_size
        self.args[Conv2DArgs.PADDING.name] = padding
        self.args[Conv2DArgs.DILATION_RATE.name] = dilation_rate
        self.args[Conv2DArgs.ACTIVATION.name] = activation

    def _filters(self):
        return self.args[Conv2DArgs.FILTERS.name]

    def _kernel_size(self):
        return self.args[Conv2DArgs.KERNEL_SIZE.name]

    def _strides(self):
        return self.args[Conv2DArgs.STRIDES.name]

    def _input_size(self):
        return self.args[Conv2DArgs.INPUT_SIZE.name]

    def _padding(self):
        return self.args[Conv2DArgs.PADDING.name]

    def _dilation_rate(self):
        return self.args[Conv2DArgs.DILATION_RATE.name]

    def _activation(self):
        return self.args[Conv2DArgs.ACTIVATION.name]

    def _single_stride(self):
        st = self._strides()
        if st[0] == 1 and st[1] == 1:
            return True
        return False

    def _single_dilation_rate(self):
        dr = self._dilation_rate()
        if dr[0] == 1 and dr[1]:
            return True
        return False

    def _mutate_filters(self, operator=MutationOperators.STEP):
        self.args[Conv2DArgs.FILTERS.name] = mutate_int(
            self._filters(), 1, Conv2DLayer.MAX_FILTER_COUNT, operator
        )

    def _mutate_kernel_size(self, operator=MutationOperators.SYNC_STEP):
        self.args[Conv2DArgs.KERNEL_SIZE.name] = mutate_tuple(
            self._kernel_size(), 1, Conv2DLayer.MAX_KERNEL_DIMENSION, operator
        )

    def _mutate_strides(self, operator=MutationOperators.SYNC_STEP):
        self.args[Conv2DArgs.STRIDES.name] = mutate_tuple(
            self._strides(), 1, Conv2DLayer.MAX_STRIDE, operator
        )

    def _mutate_padding(self):
        self.args[Conv2DArgs.PADDING.name] = mutate_enum(self._padding(), PaddingArgs)

    def _mutate_dilation_rate(self, operator=MutationOperators.SYNC_STEP):
        self.args[Conv2DArgs.DILATION_RATE.name] = mutate_tuple(
            self._dilation_rate(), 1, Conv2DLayer.MAX_DILATION, operator
        )

    def _mutate_activation(self):
        self.args[Conv2DArgs.ACTIVATION.name] = mutate_enum(
            self._activation(), Activations
        )

    def mutate(self):
        mutate_param = random.randrange(0, Conv2DLayer.MUTATABLE_PARAMETERS)

        if mutate_param == 0:
            self._mutate_filters()
        elif mutate_param == 1:
            self._mutate_kernel_size()
        elif mutate_param == 2:
            self._mutate_strides()
        elif mutate_param == 3:
            self._mutate_padding()
        elif mutate_param == 4:
            self._mutate_dilation_rate()
        elif mutate_param == 5:
            self._mutate_activation()

    def validate(self):
        if not 0 > self.args[Conv2DArgs.FILTERS.name]:
            return False

        if not self._single_stride() and not self._single_dilation_rate():
            return False

        return True

    def getkeraslayer(self):
        return keras.layers.Conv2D(
            self.args.get(Conv2DArgs.FILTERS.name),
            kernel_size=self.args.get(Conv2DArgs.KERNEL_SIZE.name),
            strides=self.args.get(Conv2DArgs.STRIDES.name),
            input_shape=self.args.get(Conv2DArgs.INPUT_SIZE.name),
            activation=self.args.get(Conv2DArgs.ACTIVATION.name),
            padding=self.args.get(Conv2DArgs.PADDING.name),
            dilation_rate=self.args.get(Conv2DArgs.DILATION_RATE.name),
        )


class MaxPool2DLayer(ModelLayer):
    MUTATABLE_PARAMETERS = 1
    MAX_POOL_SIZE = 7

    def __init__(self, pool_size, strides):
        super().__init__("MaxPool2D")
        self.args[MaxPool2DArgs.POOL_SIZE.name] = pool_size
        self.args[MaxPool2DArgs.STRIDES.name] = strides

    def getkeraslayer(self):
        return keras.layers.MaxPool2D(
            pool_size=self.args.get(MaxPool2DArgs.POOL_SIZE.name),
            strides=self.args.get(MaxPool2DArgs.STRIDES.name),
        )

    def _pool_size(self):
        return self.args[MaxPool2DArgs.POOL_SIZE.name]

    def _mutate_pool_size(self, operator=MutationOperators.SYNC_STEP):
        self.args[MaxPool2DArgs.POOL_SIZE.name] = mutate_tuple(
            self._pool_size(), 1, MaxPool2DLayer.MAX_POOL_SIZE, operator
        )
        pass

    def mutate(self):
        mutate_param = random.randrange(0, Conv2DLayer.MUTATABLE_PARAMETERS)

        if mutate_param == 0:
            self._mutate_pool_size()


class MaxPool3DLayer(MaxPool2DLayer):
    def __init__(self, pool_size, strides):
        super(MaxPool2DLayer, self).__init__("MaxPool3D")
        super().__init__(pool_size, strides)

    def getkeraslayer(self):
        return keras.layers.MaxPool3D(
            pool_size=self.args.get(MaxPool2DArgs.POOL_SIZE.name),
            strides=self.args.get(MaxPool2DArgs.STRIDES.name),
        )


class ReshapeLayer(ModelLayer):
    def __init__(self, target_shape):
        super().__init__("Reshape")
        self.args[ReshapeArgs.TARGET_SHAPE.name] = target_shape

    def getkeraslayer(self):
        target_shape = self.args.get(ReshapeArgs.TARGET_SHAPE.name)
        return keras.layers.Reshape(target_shape)


class DenseLayer(ModelLayer):
    def __init__(self, units, activation):
        super().__init__("Dense")
        self.args[DenseArgs.UNITS.name] = units
        self.args[DenseArgs.ACTIVATION.name] = activation

    def getkeraslayer(self):
        return keras.layers.Dense(
            self.args.get(DenseArgs.UNITS.name),
            activation=self.args.get(DenseArgs.ACTIVATION.name),
        )


class FlattenLayer(ModelLayer):
    def __init__(self):
        super().__init__("Flatten")

    def getkeraslayer(self):
        return keras.layers.Flatten()


class Dropout(ModelLayer):
    def __init__(self, rate):
        super().__init__("Dropout")
        self.args[DropoutArgs.RATE.name] = rate

    def getkeraslayer(self):
        rate = self.args.get(DropoutArgs.RATE.name)
        return keras.layers.Dropout(rate)
