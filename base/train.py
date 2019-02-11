import sys
sys.path.append("/home/guillefix/code/beatsaber/base")
sys.path.append("/home/guillefix/code/beatsaber")
import time
from options.train_options import TrainOptions
from data import create_dataset, create_dataloader
from models import create_model

sys.argv.append("--data_dir=../../oxai_beat_saber_data/")
sys.argv.append("--sampling_rate=16000")
sys.argv.append("--dataset_name=blockinputs")
sys.argv.append("--batch_size=1")
sys.argv.append("--gpu_ids=0")

sys.argv.pop(1)
sys.argv.pop(1)
#
# train_dataset
# import librosa
# y, sr = librosa.load(train_dataset.audio_files[0], sr=train_dataset.opt.sampling_rate)
# i=0
# [y[i:i+receptive_field] for i in range(len(y)-receptive_field+1)]
#
# len(y)/sr
#
# 190.5*60/bpm
#
# receptive_field = model.net.receptive_field
# import json
# level = json.load(open(train_dataset.level_jsons[0], 'r'))
#
# bpm = level['_beatsPerMinute']
# notes = level['_notes']
#
# import numpy as np
# blocks = np.zeros((len(y),15))
# # from math import floor
# eps = train_dataset.eps
# from math import floor, ceil
# for note in notes:
#     sample_index = int((note['_time']*60/bpm)*train_dataset.opt.sampling_rate)
#     # blocks[sample_index] = 1
#     tolerance_window_width = ceil(eps*sr)
#     for sample_delta in np.arange(-tolerance_window_width,tolerance_window_width+1):
#         # blocks[sample_index+sample_delta] = np.exp(-np.abs(sample_delta)/(2.0*tolerance_window_width))
#         blocks[sample_index+sample_delta,note["_lineLayer"]*5+note["_lineIndex"]] = note["_type"]*9+note["_cutDirection"]
#
# import matplotlib.pyplot as plt
#
# blocks[210000]
#
# plt.plot(blocks[200000:250000])

# filter = np.exp(-np.arange(len(y))/(2*train_dataset.eps*train_dataset.opt.sampling_rate)) + np.exp(-(len(y)-np.arange(len(y)))/(2*train_dataset.eps*train_dataset.opt.sampling_rate))
#
# np.convolve(blocks,filter)

# thing = train_dataset.__getitem__(0)
#
# # train_dataset
#
# thing['input'].shape
# thing['target'].shape

# foo = thing['input'].to(model.device)
# foo.type()
# model.net.module.receptive_field

# next(model.net.module.parameters()).is_cuda

# ps=list(model.net.module.parameters())
# [x.is_cuda for x in ps]
#
# model.net.module.forward(thing["input"])

# foo = model.net.module.cpu()

# next(model.net.module.parameters()).is_cuda
#
# model.net.module.state_dict

if __name__ == '__main__':
    opt = TrainOptions().parse()
    # opt["output_length"] = 32
    # opt["output_channels"] = 15
    model = create_model(opt)
    model.setup()
    if opt.gpu_ids == -1:
        receptive_field = model.net.receptive_field
    else:
        receptive_field = model.net.module.receptive_field
    print("Receptive field is "+str(receptive_field/opt.sampling_rate)+" seconds")
    train_dataset = create_dataset(opt,receptive_field = receptive_field)
    train_dataset.setup()
    train_dataloader = create_dataloader(train_dataset)
    if opt.val_epoch_freq:
        val_dataset = create_dataset(opt, validation_phase=True,receptive_field = receptive_field)
        val_dataset.setup()
        val_dataloader = create_dataloader(val_dataset)
    print('#training songs = {:d}'.format(len(train_dataset)))

    total_steps = 0

    for epoch in range(opt.epoch_count, opt.nepoch + opt.nepoch_decay):
        epoch_start_time = time.time()
        iter_data_time = time.time()
        epoch_iter = 0

        for i, data in enumerate(train_dataloader):
            iter_start_time = time.time()
            if total_steps % opt.print_freq == 0:
                t_data = iter_start_time - iter_data_time
            total_steps += opt.batch_size
            epoch_iter += opt.batch_size
            model.set_input(data)
            model.optimize_parameters()
            if total_steps % opt.display_freq == 0 or total_steps % opt.print_freq == 0:
                model.evaluate_parameters()

            if total_steps % opt.display_freq == 0:
                save_result = total_steps % opt.update_html_freq == 0

            if total_steps % opt.print_freq == 0:
                losses = model.get_current_losses()
                print(losses)
                # metrics = model.get_current_metrics()
                t = (time.time() - iter_start_time) / opt.batch_size

            if total_steps % opt.save_latest_freq == 0:
                print('saving the latest model (epoch %d, total_steps %d)' % (epoch, total_steps))
                save_suffix = 'iter_%d' % total_steps if opt.save_by_iter else 'latest'
                model.save_networks(save_suffix)

            iter_data_time = time.time()
            if i == 1:
                break

        if epoch % opt.save_epoch_freq == 0:
            print('saving the model at the end of epoch %d, iters %d' % (epoch, total_steps))
            model.save_networks('latest')
            model.save_networks(epoch)

        print('End of epoch %d / %d \t Time Taken: %d sec' %
              (epoch, opt.nepoch + opt.nepoch_decay, time.time() - epoch_start_time))
        model.update_learning_rate()

        if opt.val_epoch_freq and epoch % opt.val_epoch_freq == 0:
            val_start_time = time.time()
            with model.start_validation() as update_validation_meters:
                if opt.eval:
                    model.eval()
                for j, data in enumerate(val_dataloader):
                    val_start_time = time.time()
                    model.set_input(data)
                    model.test()
                    model.evaluate_parameters()
                    update_validation_meters()
            losses_val = model.get_current_losses(is_val=True)
            metrics_val = model.get_current_metrics(is_val=True)
            print("Validated parameters at epoch {:d} \t Time Taken: {:d} sec".format(epoch, int(time.time() - val_start_time)))

####
# model.load_networks('latest')
