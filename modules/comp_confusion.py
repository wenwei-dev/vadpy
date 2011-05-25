from vadpy.module import ComputeModule
from vadpy.options import  Option
from vadpy.labels import equalize_framelen

import logging 
log = logging.getLogger(__name__)

class ModConfusion(ComputeModule):
    """Tests elements' labels for TypeI and TypeII errors
    -----------------------------------------------------------------------
    |                           | H0 is True         | H1 is True         |
    |---------------------------|--------------------|--------------------|
    | Fail to reject H0         | Right decision     | Wrong, Type II err.|
    |                           | True positive      | False negative     |
    |---------------------------|--------------------|--------------------|
    | Reject H0                 | Wrong, Type I err. | Right decision,    |
    |                           | False positive     | True negative      |
    |---------------------------|--------------------|--------------------|

    |-----------|-----|
    | GT  | VAD | Err | Total error rate = Fn + Fp / (Tp + Fn + Tn + Fp)
    |-----|-----|-----|
    |  1  |  1  | Tp  |
    |  1  |  0  | Fn  | Fn rate = Fn / (Tp + Fn)
    |  0  |  0  | Tn  |
    |  0  |  1  | Fp  | Fp rate = Fp / (Tn + Fp)
    |-----------------|
    """
    # fscore_b = Option('fscore-b', float, "F-measurment's Beta parameter's value")
    cmp_size=Option('cmp-size', int, 'Amount of 2nd labels object frames to be treated as a single frame')

    def __init__(self, vadpy, options):
        super(ModConfusion, self).__init__(vadpy, options)

    def run(self):
        super(ModConfusion, self).run()
        assert len(set(self.inputs)) == 2, 'Confusion module requires two different inputs'

        # false positives/false negatives per source
        # the format of every tuple in dictionary is 
        # [True Positives, True Negatives, False Positives, False Negatives] tuple (list actually :)

        tp_total = 0.0
        tn_total = 0.0
        fp_total = 0.0
        fn_total = 0.0

        for element in self.vadpy.pipeline:            
            # Generate a list of decision (speech/noise) pairs for Labels objects
            # 
            gt_labels = getattr(element, self.inputs[0])
            vad_labels = getattr(element, self.inputs[1])
            
            if len(gt_labels) != len(vad_labels):
                log.warning('Labels length mismatch: {0} / {1}, equlizing frame lengths.'.format(
                        len(gt_labels), len(vad_labels)))

                equalize_framelen(gt_labels, vad_labels)

            # zip will concatenate up to min. length of the objects
            speechAB = zip((speech for start, stop, speech in gt_labels), 
                           (speech for start, stop, speech in vad_labels))

            # Calculate False alarm and Miss rate
            tp = 0; tn = 0; fp = 0; fn = 0;

            half_cmp_size = int(self.cmp_size / 2)


            for i in range(0, len(speechAB)):
                valA = speechAB[i][0]
                
                if (half_cmp_size > 0 and 
                    half_cmp_size < i < len(speechAB) - half_cmp_size):
                    valB = bool(round(sum(vAB[1] for vAB in speechAB[i - half_cmp_size : i + half_cmp_size]) 
                                 / float(self.cmp_size)))
                else:
                    valB = speechAB[i][1]

                if valA:                # concluding, valA is a value 'Speech' Ground Truth frame
                  if valB: tp += 1      # true positive
                  else:    fn += 1      # false negative, miss 
                else:                     
                  if valB: fp += 1      # false positive, false alarm
                  else:    tn += 1      # true negative
                        
            tp_total += tp
            tn_total += tn
            fp_total += fp
            fn_total += fn

        tp = tp_total 
        tn = tn_total
        fp = fp_total
        fn = fn_total

        # B2 = self.fscore_b**2
        # fscore = (1 + B2) * tp / \
        #     ((1 + B2) * tp + B2 * fn + fp)
        length = tp + tn + fp + fn;
        gt_speech = fn + tp
        gt_noise = fp + tn

        mr  = fn / (tp + fn)
        far = fp / (tn + fp)
        vur = gt_speech / gt_noise
        #total_len = tn + fn + tp + fp

        self.add_result('mr', mr)
        self.add_result('far', far)
        self.add_result('vur', vur)
        
        if self.print_flag:
            print('{0:<25}{1:.3}'.format('Miss rate:', mr))
            print('{0:<25}{1:.3}'.format('False alarm rate:', far))
            print('{0:<25}{1:.3}; ({2:.3}% speech)'.format('Speech/Non-speech rate:', vur, 100 * vur / (1 + vur)))
            print('')



