import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../../..'))
import tensorflow as tf
import copy, pprint
from data.DataManager import DataManager
from NLU.DomDect.model.input_data import *
from NLU.DomDect.model.model import *
os.environ["CUDA_VISIBLE_DEVICES"]="0"


def train(domain_dataset):
    """
    用于训练模型，先训练完存好了才能用
    :param data_tmp_path:  data tmp 文件夹位置
    """
    print('载入 Domain 模型...')
    model = DomainModel("DomDect")
    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    tf_config.allow_soft_placement=True
    with tf.Session(config=tf_config) as sess:
        sess.run(tf.group(tf.global_variables_initializer()))
        saver = tf.train.Saver()
        # saver.restore(sess, "./ckpt/model.ckpt")

        # 训练 domain detector model
        average_loss = 0
        average_accu = 0
        display_step = 100
        valid_data, valid_output = domain_dataset.produce_valid_data()
        valid_char_emb, valid_word_emb, seqlen = data_manager.sent2num(valid_data, 40, 6)
        for step in range(40000):
            batch_data, batch_output = domain_dataset.next_train_batch()
            train_char_emb, train_word_emb, seqlen = data_manager.sent2num(batch_data, 40, 6)
            _, training_loss, training_accu = sess.run([model.train_op, model.final_loss, model.accuracy],
                                        feed_dict={
                                            model.char_emb_matrix: train_char_emb,
                                            model.word_emb_matrix: train_word_emb,
                                            model.output: batch_output,
                                            model.is_training: True
                                           })
            average_loss += training_loss / display_step
            average_accu += training_accu / display_step
            if step % display_step == 0:
                valid_loss, valid_accu = sess.run([model.final_loss, model.accuracy],
                            feed_dict={
                                model.char_emb_matrix: valid_char_emb,
                                model.word_emb_matrix: valid_word_emb,
                                model.output: valid_output,
                                model.is_training: False
                               })
                print("step % 4d, train - loss: %0.4f accu: %0.4f, valid - loss: %.4f accu: %.4f"
                        % (step, average_loss, average_accu, valid_loss, valid_accu))
                average_loss = 0
                average_accu = 0

            if step == 20000:
                model.assign_lr(sess, 0.001)
            if step == 30000:
                model.assign_lr(sess, 0.0001)

        # 保存模型
        saver.save(sess, "./ckpt/model.ckpt")


def evaluate(domain_dataset):
    """
    用于训练模型，先训练完存好了才能用
    :param data_tmp_path:  data tmp 文件夹位置
    """
    print('载入 Domain 模型...')
    model = DomainModel("DomDect")

    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    tf_config.allow_soft_placement=True
    with tf.Session(config=tf_config) as sess:
        sess.run(tf.group(tf.global_variables_initializer()))
        saver = tf.train.Saver()
        saver.restore(sess, "./ckpt/model.ckpt")

        # 训练 domain detector model
        for domain in domains:
            step_count = 0
            average_loss = 0
            average_accu = 0
            domain_dataset.batch_id[domain] = 0
            while True:
                step_count += 1
                batch_data, batch_output, end_flag = domain_dataset.test_by_domain(domain, 100)
                char_emb_matrix, word_emb_matrix, seqlen = data_manager.sent2num(batch_data, 40, 6)
                loss, accu, predictions = sess.run(
                    [model.final_loss, model.accuracy, model.predict],
                    feed_dict={ model.char_emb_matrix: char_emb_matrix,
                                       model.word_emb_matrix: word_emb_matrix,
                                       model.output: batch_output,
                                       model.is_training: False})
                average_loss += loss
                average_accu += accu
                # print(testing_accu)
                if end_flag:
                    average_loss /= step_count
                    average_accu /= step_count
                    break
            print("domain:"+domain+ ", loss %0.4f, accu %0.4f" % (average_loss, average_accu))
            print("domain:"+domain+ ", num %d" %len(domain_dataset.valid_data[domain]))
            with open('test_result.txt', 'a') as f:
                f.write("domain:"+domain+ ", loss %0.4f, accu %0.4f\n" % (average_loss, average_accu))
        with open('test_result.txt', 'a') as f:
            f.write('\n')

if __name__ == '__main__':
    print('载入数据管理器...')
    data_manager = DataManager('../../../data/tmp')

    print('载入训练数据...')
    domain_dataset = generate_domain_dataset(data_manager.DialogData,
        domain_data_ids)

    train(domain_dataset)
    tf.reset_default_graph()
    evaluate(domain_dataset)

