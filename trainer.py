import tensorflow as tf
import os, code

# TODO summaries with same parameters are getting grouped together in
# tensorboard -- probably need to disambiguate them further. probably
# should check the disk for what files already exist and then bump a
# counter until a unique name is found
class Trainer:
  def __init__(self
  , model
  , x
  , y
  , load_checkpoint_filename=None
  , target_steps = 1600
  , target_cost = 0.000001
  , steps_per_summary = 10
  ):
    self.model = model
    self.x = x
    self.y = y # TODO feed this in too if (x is not y)
    self.load_checkpoint_filename = load_checkpoint_filename
    self.target_steps = target_steps
    self.target_cost = target_cost
    self.steps_per_summary = steps_per_summary
    self.learning_rate = model.lr
    self.optimizer = tf.train.AdamOptimizer(self.learning_rate) \
      .minimize(model.cost, global_step=model.global_step)
    tf.summary.scalar('cost', model.cost)
    self.summary_op = tf.summary.merge_all()
    self.log_dir_name = None
    self.writer = tf.summary.FileWriter(self.getLogDirName(), graph=tf.get_default_graph())

  def getCheckpointFilename(self):
    return '%(model)s-t-%(step)s' % {
      'model': self.model.getModelFilename()
    , 'step': self.steps_trained
    }

  def getLogDirName(self):
    if self.log_dir_name is None:
      log_dir_name_part = 'log/%(model)s-t-%(step)s-r-%%02d' % {
        'model': self.model.getModelFilename()
      , 'step': self.target_steps
      }
      n = 0
      while 1:
        log_dir_name = log_dir_name_part % n
        if not os.path.exists(log_dir_name):
          self.log_dir_name = log_dir_name
          break
        n += 1
    return self.log_dir_name

  def train(self):
    keep_training = True
    x = self.x

    # How many steps trained so far?
    self.steps_trained = 0

    with tf.Session(config=tf.ConfigProto(intra_op_parallelism_threads=1)) as sess:
      saver = tf.train.Saver()
      init = tf.global_variables_initializer()
      sess.run(init)
      if self.load_checkpoint_filename:
        saver.restore(sess, self.load_checkpoint_filename)
        print('model restored')
        # TODO restore epochs counter!

      while keep_training:
        try:
          # 
          feed_dict = {
            self.model.x: self.x
          }
          if not self.model.auto_encoder:
            feed_dict[self.model.y] = self.y
          sess.run(self.optimizer, feed_dict=feed_dict)
          if self.steps_trained % self.steps_per_summary == 0:
            training_cost, summary = sess.run(
              [self.model.cost, self.summary_op]
            , feed_dict=feed_dict
            )
            print('% 7d/% 7d cost=%.9f' % (
              self.steps_trained
            , self.target_steps
            , training_cost
            ))
            self.writer.add_summary(summary, self.steps_trained)

            if training_cost <= self.target_cost:
              print('target cost achieved, no more training')
              break
          self.steps_trained += 1
          if self.steps_trained > self.target_steps:
            keep_training = False
        except KeyboardInterrupt as e:
          print()
          print()
          print('entering interactive shell')
          print('REMEMBER not to raise SYSTEMEXIT if you want your model saved!!!')
          print('to save and quit, assign keep_training=False')
          print()
          print()
          code.interact(local=locals())

      # save checkpoint
      checkpoint_filename = self.getCheckpointFilename()
      saver.save(sess, 'checkpoints/' + checkpoint_filename)
      print('model saved')