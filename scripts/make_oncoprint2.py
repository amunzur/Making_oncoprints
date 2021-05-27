#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  7 16:43:00 2021

@author: amunzur
"""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

# load utilities functions to make the oncoprint
exec(open("/groups/wyattgrp/users/amunzur/ind232/scripts/utilities_make_oncoprint.py").read())

########################
# DEFINE VARIABLES
########################

# PATH_sample_ids = "/groups/wyattgrp/users/amunzur/onboarding/data/m1rp_patient_sample_IDs.tsv"
PATH_cn = "/groups/wyattgrp/users/amunzur/ind232/data/ind232_CN.csv"
PATH_muts = "/groups/wyattgrp/users/amunzur/ind232/data/ind232_muts.csv"
PATH_figure = "/groups/wyattgrp/users/amunzur/ind232/figures/ind232_oncoprint.pdf"

patient_id = "" # leave blank (an empty string) to show all patients
filter_ctDNA = True # True means only keep the sample with higher ctDNA content from a patient. Or write False to keep all samples
sort_sample_type = True # gather together EOT and baseline samples. Otherwise no ordering

########################
# READ FILES
########################

# read the dataframes based on type
if PATH_cn.split(".")[1] == "tsv": 
    df_cn = pd.read_csv(PATH_cn, sep = "\t")
    df_muts = pd.read_csv(PATH_muts, sep = "\t")

elif PATH_cn.split(".")[1] == "csv":
    df_cn = pd.read_csv(PATH_cn)
    df_muts = pd.read_csv(PATH_muts)

# if patient id is given, filter for that 
if patient_id:
    df_cn = df_cn.loc[df_cn['Patient ID'] == patient_id]
    df_muts = df_muts.loc[df_muts['Patient ID'] == patient_id]
else:
    pass

########################
# MODIFY FILES
########################

# make sure the genes are in the rows and samples are columns 
if df_cn.index.name is None: # if the index hasn't been set
    df_cn = df_cn.drop(columns=['DNA repair defect']) # drop unneeded cols for the oncoprint
    df_cn = pd.melt(df_cn, id_vars = ["Sample", "ctDNA fraction", "Mutation count", "Responder_status"], var_name='Gene', value_name='Copy number')
    
# add two cols for patient id and sample
df_cn[["Patient ID", "Sample type"]] = df_cn["Sample"].str.split(pat = "_", expand = True).rename(columns = {0:"Patient ID", 1:"Sample type"}) # separate sample name from the patient id 
df_muts[["Patient ID", "Sample type"]] = df_muts["Sample"].str.split(pat = "_", expand = True).rename(columns = {0:"Patient ID", 1:"Sample type"}) # separate sample name from the patient id

df_cn["ctDNA fraction"] = df_cn["ctDNA fraction"] * 100 # convert fraction to percentage 

# make a new df for sample_type colors 
df_type = df_cn.drop_duplicates(subset = ["Sample"])

# filtering
if filter_ctDNA == True:
    df_cn = filter_df_ctDNA(df_cn) # filter based on ctDNA content
    df_muts = df_muts[df_muts["Sample"].isin(df_cn["Sample"])] # filter df_muts to keep samples from df_cn
else: 
    pass

if sort_sample_type == True:
    
    # ordering based on sample type 
    df_cn = df_cn.sort_values(by = "Sample type")
    df_muts = df_muts.sort_values(by = "Sample type")
    
    # order based on ctDNA content, within the groups
    df_cn = df_cn.groupby("Sample type").apply(pd.DataFrame.sort_values, 'ctDNA fraction')
    # df_muts = df_muts.groupby("Sample type").apply(pd.DataFrame.sort_values, 'ctDNA fraction')
    
    df_cn = df_cn.reset_index(drop = True)
    df_muts = df_muts.reset_index(drop = True)
    
# sort df_cn once more based on ctDNA fraction, from high to low
df_cn = df_cn.sort_values(by = ["ctDNA fraction"])
    
########################
# COLORS and SHAPES
########################
sample_type_dict = {"EOT": "#CC6677", "Baseline": "#DDCC77"}
df_cn["sample_type_color"] = df_cn["Sample type"].map(sample_type_dict)

cn_dict = {-2:'#3f60ac', -1:'#9cc5e9', 0:'#e6e7e8', 1:'#f59496', 2:'#ee2d24'}
df_cn['Color'] = df_cn['Copy number'].map(cn_dict)

mut_dict = {'Missense mutation':'#79B443', 'Splice site mutation':'#FFC907', 'Splice site mutation ': '#FFC907',
               'Stopgain mutation':'#FFC907', 'Frameshift mutation':'#FFC907', 'Frameshift indel':'#5c32a8', 'Non-frameshift indel':'#BD4398',
               'Germline frameshift mutation':'#FFC907', 'Germline stopgain mutation':'#FFC907', 'Germline missense mutation':'#79B443',
               'Intragenic arrangement': "#a3dcf7", "Multiple somatic mutations": "black"}

df_muts['Color'] = df_muts['Effect'].map(mut_dict)

shape_dict = {'Missense mutation':'s', 'Splice site mutation':'s', 'Splice site mutation ': 's',
               'Stopgain mutation':'s', 'Frameshift mutation':'s', 'Frameshift indel':'s', 'Non-frameshift indel':'s',
               'Germline frameshift mutation':'*', 'Germline stopgain mutation':'*', 'Germline missense mutation':'*',
               'Intragenic arrangement': "s", "Multiple somatic mutations": "^"}
df_muts["shapes"] = df_muts["Effect"].map(shape_dict)

########################
# DIVIDE THE DATAFRAMES
########################
[df_cn1, df_cn2] = filter_df_by_col(df_cn, "Responder_status") # not responsive
[df_muts1, df_muts2] = filter_df_by_col(df_muts, "Responder_status") # responsive

df_counts1 = plot_mut_and_cn_counts(df_cn1, df_muts1, drop = True) # not responsive
df_counts2 = plot_mut_and_cn_counts(df_cn2, df_muts2, drop = True) # responsive

# make sure both dfs have the same genes, replace with 0 if exists in one df only
genes_to_add = df_counts1[~df_counts1.index.isin(df_counts2.index)].dropna().index.to_list()
df_zero = pd.DataFrame(0, index = genes_to_add, columns = df_counts1.columns) # df of 0s

df_counts2 = pd.concat([df_counts2, df_zero]) # update by adding a df of zeros to replace missing genes

#Dict to map genes to row on oncoprint  
samples1 = df_cn1["Sample"].unique().tolist()
samples2 = df_cn2["Sample"].unique().tolist()
genes = df_cn['Gene'].unique().tolist()
             
gene_pos = {genes[i]: list(range(0,len(genes)))[i] for i in range(len(genes))}
sample_pos1 = {samples1[i]: list(range(0,len(samples1)))[i] for i in range(len(samples1))}
sample_pos2 = {samples2[i]: list(range(0,len(samples2)))[i] for i in range(len(samples2))}

ordered_patients_list1 = [sample.split(sep = "_")[0] for sample in samples1]
ordered_patients_list2 = [sample.split(sep = "_")[0] for sample in samples2]

# order counts dfs based on the gene positions set above
df_counts1 = df_counts1.reindex(list(gene_pos.keys()))
df_counts2 = df_counts2.reindex(list(gene_pos.keys()))

# calculate the PERCENTAGE instead of absolute counts
df_counts1 = convert_counts_to_percentage(25, 2, 2, df_cn1, df_counts1)
df_counts2 = convert_counts_to_percentage(25, 2, 2, df_cn2, df_counts2)

########################
# PREPARE TO PLOT
########################    
fig_width = 8
fig_height = 9

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams["font.size"] = "6"

bar_height = 0.7
bar_width = 0.7

# offset = -(bar_height/3)
offset = -0.4

fig = plt.figure(figsize=(fig_width, fig_height))
gs  = gridspec.GridSpec(nrows=4, ncols=4, height_ratios = [1.5, 1.5, 15, 13], width_ratios = [7, 0.5, 1.6, 0.5], wspace = 0.02, hspace=0.02)
# gs.update(wspace=0.015, hspace=0.05)# set the spacing between axes. 

top1 = fig.add_subplot(gs[0,0]) # ctDNA
mutcount1 = fig.add_subplot(gs[1,0], sharex = top1) # mut count
bottom1 = fig.add_subplot(gs[2,0], sharex = mutcount1) # heatmap
count1 = fig.add_subplot(gs[2,1], sharey = bottom1)

top2 = fig.add_subplot(gs[0,2], sharey = top1) # ctDNA
mutcount2 = fig.add_subplot(gs[1,2], sharex = top2, sharey = mutcount1) # mutcount
bottom2 = fig.add_subplot(gs[2,2], sharex = mutcount2) #heatmap
count2 = fig.add_subplot(gs[2, 3], sharey = bottom2)

sub_legend = fig.add_subplot(gs[3,:])

########################
# PLOTTING
########################
# Plot ctDNA fraction in the top subplot
top1.bar(df_cn1["Sample"], df_cn1["ctDNA fraction"], color = "#202020", zorder = 3)
top2.bar(df_cn2["Sample"], df_cn2["ctDNA fraction"], color = "#202020", zorder = 3)

# plot the mutation count 
mutcount1.bar(df_cn1["Sample"], df_cn1["Mutation count"], color = "#202020", zorder = 3)
mutcount2.bar(df_cn2["Sample"], df_cn2["Mutation count"], color = "#202020", zorder = 3)

# plot copy numbers
plot_cn(samples1, genes, df_cn1, bottom1, offset, bar_height, bar_width)
plot_cn(samples2, genes, df_cn2, bottom2, offset, bar_height, bar_width)

# plot mutations     
plot_muts(sample_pos1, gene_pos, df_muts1, bottom1)
plot_muts(sample_pos2, gene_pos, df_muts2, bottom2)

# plot CN and mut count bar graphs 
width = 0.315

a = dict(zip(gene_pos.keys(), [x - width/1.92 - 0.07 for x in gene_pos.values()]))
b = dict(zip(gene_pos.keys(), [x + width/2.7 for x in gene_pos.values()]))

count1.barh(list(a.values()), df_counts1.CN_changes_perc, width, color = "#B0B0B0")
count1.barh(list(b.values()), df_counts1.Mutation_events, width, color='#404040')

count2.barh(list(a.values()), df_counts2.CN_changes_perc, width, color = "#B0B0B0")
count2.barh(list(b.values()), df_counts2.Mutation_events_perc, width, color="#404040")
########################
# STYLING
########################
for ax in [top2, mutcount2]:
    ax.xaxis.set_visible(False)

# Baseline ctDNA plot, top left
top1.set_xticks([])
top1.set_yticks([0, 50, 100])
top1.set_yticklabels(["0", "50", "100"])
top1.set_ylabel("ctDNA %", labelpad=17, rotation = 0, va = 'center')
top1.grid(zorder = 0, linestyle='--', linewidth = 0.5, axis = "y")
top1.tick_params(labelbottom=False)

# Baseline mutation count plot, middle left
mutcount1.set_xticks([])
mutcount1.set_yticks([0, 25, 50])
mutcount1.set_yticklabels(["0", "25", "50"])
mutcount1.set_ylabel("Total \nmutation \ncount", labelpad=20, rotation = 0, va = 'center')
mutcount1.grid(zorder = 0, linestyle='--', linewidth = 0.5, axis = "y")
mutcount1.tick_params(labelbottom=False)

# Baseline heatmap, bottom left
bottom1.tick_params(labelrotation = 90, direction = "out", pad = 3)
bottom1.set_yticks(list(range(0, len(genes))))
bottom1.set_yticklabels(genes, rotation = 0, ha = 'right')
bottom1.set_xticks(list(range(0, len(ordered_patients_list1))))
bottom1.set_xlim([-1, len(samples1) - 0.5])
bottom1.set_xticklabels(ordered_patients_list1, ha = "center")

# EOT ctDNA plot, top right
top2.set_yticks([0, 50, 100])
top2.grid(zorder = 0, linestyle='--', linewidth = 0.5)
plt.setp(top2.get_yticklabels(), visible=False) # remove tick labels from eot plot only

# EOT mutation count plot, middle right
mutcount2.grid(zorder = 0, linestyle='--', linewidth = 0.5)
plt.setp(mutcount2.get_yticklabels(), visible=False)

# EOT heatmap, bottom right
bottom2.yaxis.set_visible(False)
bottom2.tick_params(labelrotation = 90, direction = "out", pad = 7)
bottom2.set_xticks(list(range(0, len(ordered_patients_list2))))
bottom2.set_xticklabels(ordered_patients_list2)
bottom2.set_xlim([-1, len(samples2) - 0.55])

sub_legend.xaxis.set_visible(False)
sub_legend.yaxis.set_visible(False)
sub_legend.set_facecolor("none")

# counts bar graphs
count1.tick_params(labelrotation = 90, direction = "out", pad = 0.2)
count1.set_xticks([0, 50, 100])
count1.set_xticklabels(["0", "50", "100"])
count1.xaxis.set_tick_params(width = 0.5)
count1.spines['right'].set_visible(False)
count1.spines['left'].set_visible(False)
count1.spines['top'].set_visible(False)
count1.spines['bottom'].set_linewidth(0.5)
count1.tick_params(axis='y', length=0)
plt.setp(count1.get_yticklabels(), visible=False)

count2.tick_params(labelrotation = 90, direction = "out", pad = 0.2)
count2.set_xticks([0, 50, 100])
count2.set_xticklabels(["0", "50", "100"])
count2.xaxis.set_tick_params(width = 0.5)
count2.spines['right'].set_visible(False)
count2.spines['left'].set_visible(False)
count2.spines['top'].set_visible(False)
count2.spines['bottom'].set_linewidth(0.5)
count2.axes.yaxis.set_ticks([])
plt.setp(count2.get_yticklabels(), visible=False)

for ax in [top1, mutcount1, bottom1, top2, mutcount2, bottom2, sub_legend]: 
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')
    
########################
# LEGEND
########################
legend_cn_dict = {"Deep deletion":'#3f60ac', "Deletion":'#9cc5e9', "Neutral":'#e6e7e8', "Gain":'#f59496', "Amplification":'#ee2d24'}

mut_dict = {'Missense':'#79B443', 'Splice site, stopgain, frameshift':'#FFC907', 'Frameshift indel':'#5c32a8', 'Non-frameshift indel':'#BD4398', '>2 mutations': 'black'}

mut_dict_shape = {'Somatic':'s', 'Germline':'*'}

# legend1
handles_cn = []
for key in legend_cn_dict:
    handle = mpatches.Patch(color = legend_cn_dict.get(key), label = key)
    handles_cn.append(handle)

# legend2
handles_muts = []
for key in mut_dict:   
    handle = mpatches.Patch(color = mut_dict.get(key), label = key)
    handles_muts.append(handle)

# legend3
handle_cn = mpatches.Patch(color = "#B0B0B0", label = "Copy number variants")
handle_mut = mpatches.Patch(color = "#404040", label = "Mutations")
handles_counts = [handle_cn, handle_mut]

# legend4
handles_mut_shapes = []
for key in mut_dict_shape:    
    handle = Line2D([0], [0], linestyle = "none", marker = mut_dict_shape.get(key), label = key, markerfacecolor = mut_dict.get(key), color = "#B0B0B0", markersize=5, markeredgewidth = 0)
    handles_mut_shapes.append(handle)

legend1 = fig.legend(handles=handles_cn, bbox_to_anchor=(0.29, 0.32), frameon=False, title = "Copy number variants", title_fontsize = 7)
legend2 = fig.legend(handles=handles_muts, bbox_to_anchor=(0.52, 0.32), frameon=False, title = "Mutations", title_fontsize = 7)
legend3 = fig.legend(handles=handles_counts, bbox_to_anchor=(0.71, 0.32), frameon=False, title = "Copy number change and \nmutation percentages", title_fontsize = 7)
legend4 = fig.legend(handles=handles_mut_shapes, bbox_to_anchor=(0.397, 0.23), frameon=False)

# align the legend titlesshapes_dict = {}
legend1._legend_box.align = "left"
legend2.get_title().set_position((-40, 0))
legend3._legend_box.align = "left"

# plt.plot([0, 0], [1, 1], 'k-', lw=2)
plt.axhline(y = 0.75, xmin = 0.01, xmax = bottom1.get_position().x1 + 0.03, color='black', linestyle='-')
plt.axhline(y = 0.75, xmin = 0.795, xmax = 0.94, color='black', linestyle='-')

plt.text(0.28, 0.68, "Best response PD", fontsize = 9)
plt.text(0.84, 0.68, "PR/SD", fontsize = 9)

fig.savefig("/groups/wyattgrp/users/amunzur/ind232/figures/fig.pdf", bbox_extra_artists=(), bbox_inches='tight')
plt.show()








