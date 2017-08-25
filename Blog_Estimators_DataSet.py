import tensorflow as tf
import collections
import os
import urllib
import numpy as np
import sys

# Check that we have correct TensorFlow version installed
tf_version = tf.__version__
print("TensorFlow version: {}".format(tf_version))
assert "1.3" <= tf_version, "TensorFlow r1.3 or later is needed"

# Windows users: You only need to change PATH, rest is platform independent
PATH = "/tmp/tf_dataset_and_estimator_apis"

# Fetch and store Training and Test dataset files
PATH_DATASET = PATH +os.sep + "dataset"
FILE_TRAIN =   PATH_DATASET + os.sep + "iris_training.csv"
FILE_TEST =    PATH_DATASET + os.sep + "iris_test.csv"
URL_TRAIN =   "http://download.tensorflow.org/data/iris_training.csv"
URL_TEST =    "http://download.tensorflow.org/data/iris_test.csv"
def downloadDataset(url, file):
    if not os.path.exists(PATH_DATASET):
        os.makedirs(PATH_DATASET)
    if not os.path.exists(file):
        data = urllib.urlopen(url).read()
        with open(file, "w") as f:
            f.write(data)
            f.close()
downloadDataset(URL_TRAIN, FILE_TRAIN)
downloadDataset(URL_TEST, FILE_TEST)

tf.logging.set_verbosity(tf.logging.INFO)

# The CSV fields in the files
dataset_fields = collections.OrderedDict([
    ('SepalLength',    [0.]), # tf.float32
    ('SepalWidth',     [0.]), # tf.float32
    ('PetalLength',    [0.]), # tf.float32
    ('PetalWidth',     [0.]), # tf.float32
    ('IrisFlowerType', [0])   # tf.int32
])

# Create an input function reading a file using the Dataset API
# Then provide the results to the Estimator API
def my_input_fn(file_path, repeat_count):
    def decode_csv(line):
        parsed = tf.decode_csv(line, list(dataset_fields.values()))
        features = parsed[:-1]
        label = parsed[-1:]
        return dict(zip(dataset_fields.keys(), features)), label

    dataset = (
        tf.contrib.data.TextLineDataset(file_path) # Read text line file
            .skip(1) # Skip header row
            .map(decode_csv) # Transform each elem by applying decode_csv fn
            .shuffle(buffer_size=1) # Obs: buffer_size is read into memory
            .repeat(repeat_count) #
            .batch(32)) # Batch size to use
    iterator = dataset.make_one_shot_iterator()
    batch_features, batch_labels = iterator.get_next()
    return batch_features, batch_labels

# nb = my_input_fn(FILE_TRAIN, 1)
# with tf.Session() as sess:
#     nr = sess.run(nb)
#     print len(nr[1])
# sys.exit()

# Create the feature_columns, which specifies the input to our model
# All our input features are numeric, so use numeric_column for each one
feature_names = dataset_fields.copy() # Create a list of our input features
del feature_names['IrisFlowerType'] # Remove the label field
feature_columns = [tf.feature_column.numeric_column(k) for k in feature_names]

# Create a deep neural network regression classifier
# Use the DNNRegressor canned estimator
classifier = tf.estimator.DNNClassifier(
    feature_columns=feature_columns, # The input features to our model
    hidden_units=[10, 10], # Two layers, each with 10 neurons
    n_classes=3,
    model_dir=PATH) # Path to where checkpoints etc are stored

# Train our model, use the previously function my_input_fn
# Input to training is a file with training example
# Stop training after 2000 batches have been processed
classifier.train(
    input_fn=lambda: my_input_fn(FILE_TRAIN, None),
    steps=2000)

# Evaluate our model using the examples contained in FILE_TEST
# Return value will contain evaluation_metrics such as: loss & average_loss
evaluate_result = classifier.evaluate(
    input_fn=lambda: my_input_fn(FILE_TEST, None),
    steps=2000)
print("Evaluation results")
for key in evaluate_result:
    print("   {}, was: {}".format(key, evaluate_result[key]))

# Let create a dataset for prediction
# We've taken the first 3 examples in FILE_TEST
prediction_input = [[5.9, 3.0, 4.2, 1.5],  # -> 1, Iris Versicolor
                    [6.9, 3.1, 5.4, 2.1],  # -> 2, Iris Virginica
                    [5.1, 3.3, 1.7, 0.5]]  # -> 0, Iris Sentosa
def new_input_fn():
    def decode(x):
        x = tf.split(x, 4) # Need to split into our 4 features
        return dict(zip(feature_names, x)) # To build a dict of them

    dataset = tf.contrib.data.Dataset.from_tensor_slices(prediction_input)
    dataset = dataset.map(decode)
    iterator = dataset.make_one_shot_iterator()
    next_feature_batch = iterator.get_next()
    return next_feature_batch, None # In prediction, we have no labels

# Predict all our prediction_input
predict_results = classifier.predict(input_fn=new_input_fn)

# Print results
for idx, prediction in enumerate(predict_results):
    type = prediction["class_ids"][0] # Get the predicted class (index)
    if type == 0:
        print("I think: {}, is Iris Sentosa".format(prediction_input[idx]))
    elif type == 1:
        print("I think: {}, is Iris Versicolor".format(prediction_input[idx]))
    else:
        print("I think: {}, is Iris Virginica".format(prediction_input[idx]))
