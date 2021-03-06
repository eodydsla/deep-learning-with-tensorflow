import os
import numpy as np
import tensorflow as tf
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

np.random.seed(0)
tf.set_random_seed(1234)

'''
로그 파일을 위한 설정
'''
LOG_DIR = os.path.join(os.path.dirname(__file__), 'log')

if os.path.exists(LOG_DIR) is False:
    os.mkdir(LOG_DIR)


def inference(x, keep_prob, n_in, n_hiddens, n_out):
    def weight_variable(shape, name=None):
        initial = np.sqrt(2.0 / shape[0]) * tf.truncated_normal(shape)
        return tf.Variable(initial, name=name)

    def bias_variable(shape, name=None):
        initial = tf.zeros(shape)
        return tf.Variable(initial, name=name)

    with tf.name_scope('inference'):
        # 입력층-은닉층, 은닉층-은닉층
        for i, n_hidden in enumerate(n_hiddens):
            if i == 0:
                input = x
                input_dim = n_in
            else:
                input = output
                input_dim = n_hiddens[i-1]

            W = weight_variable([input_dim, n_hidden],
                                name='W_{}'.format(i))
            b = bias_variable([n_hidden],
                              name='b_{}'.format(i))

            h = tf.nn.relu(tf.matmul(input, W) + b,
                           name='relu_{}'.format(i))
            output = tf.nn.dropout(h, keep_prob,
                                   name='dropout_{}'.format(i))

        # 은닉층-출력층
        W_out = weight_variable([n_hiddens[-1], n_out], name='W_out')
        b_out = bias_variable([n_out], name='b_out')
        y = tf.nn.softmax(tf.matmul(output, W_out) + b_out, name='y')
    return y


def loss(y, t):
    with tf.name_scope('loss'):
        cross_entropy = \
            tf.reduce_mean(-tf.reduce_sum(
                           t * tf.log(tf.clip_by_value(y, 1e-10, 1.0)),
                           reduction_indices=[1]))
    tf.summary.scalar('cross_entropy', cross_entropy)
    return cross_entropy


def training(loss):
    with tf.name_scope('training'):
        optimizer = tf.train.AdamOptimizer(learning_rate=0.001,
                                           beta1=0.9,
                                           beta2=0.999)
    train_step = optimizer.minimize(loss)
    return train_step


def accuracy(y, t):
    with tf.name_scope('accuracy'):
        correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(t, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    return accuracy


if __name__ == '__main__':
    '''
    데이터를 생성한다
    '''
    mnist = datasets.fetch_mldata('MNIST original', data_home='.')

    n = len(mnist.data)
    N = 30000  # MNIST의 일부를 사용한다
    N_train = 20000
    N_validation = 4000
    indices = np.random.permutation(range(n))[:N]  # 무작위로 N장을 선택한다

    X = mnist.data[indices]
    X = X / 255.0
    X = X - X.mean(axis=1).reshape(len(X), 1)
    y = mnist.target[indices]
    Y = np.eye(10)[y.astype(int)]  # 1-of-K 표현으로 변환한다

    X_train, X_test, Y_train, Y_test = \
        train_test_split(X, Y, train_size=N_train)

    X_train, X_validation, Y_train, Y_validation = \
        train_test_split(X_train, Y_train, test_size=N_validation)

    '''
    모델을 설정한다
    '''
    n_in = len(X[0])
    n_hiddens = [200, 200, 200]  # 각 은닉층의 차원 수
    n_out = len(Y[0])
    p_keep = 0.5

    x = tf.placeholder(tf.float32, shape=[None, n_in], name='x')
    t = tf.placeholder(tf.float32, shape=[None, n_out], name='t')
    keep_prob = tf.placeholder(tf.float32, name='keep_prob')

    y = inference(x, keep_prob, n_in=n_in, n_hiddens=n_hiddens, n_out=n_out)
    loss = loss(y, t)
    train_step = training(loss)

    accuracy = accuracy(y, t)

    '''
    모델을 학습시킨다
    '''
    epochs = 50
    batch_size = 200

    init = tf.global_variables_initializer()
    sess = tf.Session()

    summaries = tf.summary.merge_all()
    file_writer = tf.summary.FileWriter(LOG_DIR, sess.graph)

    sess.run(init)

    n_batches = N_train // batch_size

    for epoch in range(epochs):
        X_, Y_ = shuffle(X_train, Y_train)

        for i in range(n_batches):
            start = i * batch_size
            end = start + batch_size

            sess.run(train_step, feed_dict={
                x: X_[start:end],
                t: Y_[start:end],
                keep_prob: p_keep
            })

        # 검증 데이터를 사용해서 평가한다
        summary, val_loss = sess.run([summaries, loss], feed_dict={
            x: X_validation,
            t: Y_validation,
            keep_prob: 1.0
        })
        file_writer.add_summary(summary, epoch)

        print('epoch:', epoch,
              ' validation loss:', val_loss)

    '''
    예측 정확도를 평가한다
    '''
    accuracy_rate = accuracy.eval(session=sess, feed_dict={
        x: X_test,
        t: Y_test,
        keep_prob: 1.0
    })
    print('accuracy: ', accuracy_rate)
