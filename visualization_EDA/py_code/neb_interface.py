from flask import Flask, render_template, request
import pandas as pd
from sqlalchemy import create_engine

from bokeh import __version__ as BOKEH_VERSION
from bokeh.embed import components
from bokeh.layouts import column, widgetbox, WidgetBox, layout

# For the button and a hovertool
from bokeh.models import CustomJS, Button, HoverTool, ColumnDataSource, \
                         LinearColorMapper, BasicTicker, PrintfTickFormatter, \
                         ColorBar, OpenURL, TapTool
# For the sliders and dropdown
from bokeh.models.widgets import MultiSelect, Paragraph, PreText, CheckboxGroup, Slider, \
                                 Dropdown, Select, RangeSlider
from bokeh.plotting import figure, curdoc, show

import numpy as np
import pdb
from random import random



app = Flask(__name__)

@app.route('/')
def home():

    #Access the SQL database
    engine = create_engine('sqlite:///../tapestation.db', echo=False)

    #Make a plot of strongest peaks, sizes and peak molarity

    #Get the data
    peak_df = pd.read_sql('SELECT * FROM peaks', engine)

    #Get region data
    region_df = pd.read_sql('SELECT * from regions', engine)
    region_cols = ['ts_data_id', 'well_id', 'avg_size']
    region_size_df = region_df[region_cols]

        
    #Choose only the first peak as well as from samples only
    first_peak_mask = (peak_df['samp_desc'] != 'Electronic Ladder') & (peak_df['peak_id'] == 1)
    first_peak_df = peak_df[first_peak_mask].copy()
    first_peak_cols = ['ts_data_id', 'well_id', 'peak_mol', 'int_area', 'size', 'cal_conc']
    first_peak_df = first_peak_df[first_peak_cols]

    #Merging the data
    combined_df = pd.merge(first_peak_df, region_size_df, on=['ts_data_id', 'well_id'], how='outer')
    #print(combined_df)
    source_data = ColumnDataSource(combined_df)

    #Have two instances of the data so for callback purposes
    #Because we are essentially filtering the data
    #We don't want to lose the data when altering widgets, keep an 'unchanged' copy
    unchanged_data = ColumnDataSource(combined_df)

    first_peak_plot = figure()
    first_peak_plot.circle(x='size', y='peak_mol', source=source_data)

    first_peak_plot.title.text = 'Size vs Peak Molarity of Strongest Peaks'
    first_peak_plot.xaxis.axis_label = 'Size [bp]'
    first_peak_plot.yaxis.axis_label = 'Peak Molarity [pmol/l]'

    #Add a hover tool for the relevant information from peaks table
    hover_first_peak = HoverTool()
    hover_first_peak.tooltips=[
            ('TS Data ID', '@ts_data_id'),
            ('Well', '@well_id'),
            ('Size [bp]','@size'),
            ('Peak Molarity [pmol/l]', '@peak_mol'),
            ('Calibrated Concentration [pg/mul]', '@cal_conc'),
            ('% Integrated Area', '@int_area')
            ]
    first_peak_plot.add_tools(hover_first_peak)


    #Make a plot comparing well size to average size
    size_plot = figure(match_aspect=True) #match_aspect keep aspect ratio the same
    size_plot.circle(x='size', y='avg_size', source=source_data)

    size_plot.title.text = 'Size of Strongest Peak vs Avg Size of Region [bp]'
    size_plot.xaxis.axis_label = 'Size of Strongest Peak [bp]'
    size_plot.yaxis.axis_label = 'Avg Size of Region [bp]'

    size_plot.ray(x=[0,2,3], y=[0,2,3], length=0, angle=[45], angle_units='deg', color="#FB8072")
    #Add a hover tool for the relevant information
    hover_size = HoverTool()
    hover_size.tooltips = [
            ('TS Data ID', '@ts_data_id'),
            ('Well', '@well_id'),
            ('Size [bp]', '@size'),
            ('Avg size [bp]', '@avg_size')
            ]

    size_plot.add_tools(hover_size)


    #Slider callbacks with CustomJS
    callback_JS="""
    //Get the value from out int area slider
    var int_area_cutoff = int_area_slider.value;

    //Get the range of our calibrated concentration slider
    var conc_min = conc_slider.value[0];
    var conc_max = conc_slider.value[1];

    //Get the values from ts data multi_select
    var ts_data_list = ts_data_multi_select.value;
    //console.log(ts_data_list);

    //Call the unchanged data
    var uc_data = unchanged_data.data;
    var uc_ts_data_id_data = uc_data['ts_data_id'];
    var uc_well_id_data = uc_data['well_id'];
    var uc_cal_conc_data = uc_data['cal_conc'];
    var uc_int_area_data = uc_data['int_area'];
    var uc_size_data = uc_data['size'];
    var uc_peak_mol_data = uc_data['peak_mol'];
    var uc_avg_size = uc_data['avg_size'];

    //Call the data that we'll change
    var data = source_data.data;

    //The four columns we will change are cal_conc, int_area, size, and peak_mol
    var cal_conc=[];
    var int_area=[];
    var size=[];
    var peak_mol=[];
    var ts_data_id = [];
    var well_id = [];
    var avg_size = [];

    //Filter the data
    for(var i=0; i<uc_cal_conc_data.length;i++){
        if(uc_int_area_data[i] >= int_area_cutoff){
            if(uc_cal_conc_data[i] >= conc_min && uc_cal_conc_data[i] <= conc_max){
                if(ts_data_list.includes(uc_ts_data_id_data[i])){
                cal_conc.push(uc_cal_conc_data[i]);
                int_area.push(uc_int_area_data[i]);
                size.push(uc_size_data[i]);
                peak_mol.push(uc_peak_mol_data[i]);
                ts_data_id.push(uc_ts_data_id_data[i]);
                well_id.push(uc_well_id_data[i]);
                avg_size.push(uc_avg_size[i]);
                }
            }
        }
    }

    //Change the index too, since lengths are not the same any longer
    var index=[];
    for(var j=0; j<cal_conc.length;j++){
        index.push(j);
    }

    //Replace the data and emit it to source
    data['ts_data_id'] = ts_data_id;
    data['well_id'] = well_id;
    data['cal_conc'] = cal_conc;
    data['int_area'] = int_area;
    data['size'] = size;
    data['peak_mol'] = peak_mol;
    data['index'] = index;
    data['avg_size'] = avg_size;
    //console.log(data)

    source_data.change.emit();
    """
    callback = CustomJS(args=dict(source_data=source_data, unchanged_data=unchanged_data), code=callback_JS)

    # Want to make a slider for integrate_area cutoff
    int_area_N = 0
    int_area_slider = Slider(start=0, end=100, step=1, value = int_area_N, title="% Integrated Area Cutoff")
    int_area_slider.js_on_change('value', callback)
    #Want to make a rangeslider for calibrated concentration
    cal_conc_min = first_peak_df['cal_conc'].min()
    cal_conc_max = first_peak_df['cal_conc'].max()
    conc_slider = RangeSlider(start=cal_conc_min, end=cal_conc_max, value=(cal_conc_min, cal_conc_max),step=(cal_conc_max - cal_conc_min) / 100, title='Range of Calibrated Concentration [pg/mul]')
    conc_slider.js_on_change('value',callback)


    #Make a Multiselect tool
    ts_data_list = first_peak_df['ts_data_id'].unique().tolist()
    ts_data_multi_select = MultiSelect(title='Select Data: ', value=ts_data_list, options=ts_data_list, height=130)
    ts_data_multi_select.js_on_change('value',callback)


    #Callback arguments
    callback.args['int_area_slider'] = int_area_slider
    callback.args['conc_slider'] = conc_slider
    callback.args['ts_data_multi_select'] = ts_data_multi_select


    #Create a paragraph to discuss first two plots
    readme = Paragraph(text = """
    These first two plots correspond to the strongest peaks of the datasets.  The first plot showing the size vs peak molarity, where the second plot shows the size vs the average size of the region. 

    The user can use the following tools to filter the data being plotted.  
    'Select Data' is a MultiSelect Table,from which users can select which data to plot. 
    'Range of Calibrated Concentration allows users to choose the range of calibrated concentration.
    '% Integrated Area Cutoff allows user to choose the minimum required % Integrated Area for the strongest peak.
    """, width=1000)

    #Make another plot of the lower markers and the upper markers
    #marker_df = pd.read_sql('SELECT * FROM markers', engine)
    #marker_cols = ['ts_data_id', 'well_id', 'peak_mol', 'int_area', 'size', 'cal_conc', 'marker_id']
    #marker_df = marker_df[marker_cols]

    #Separate the two
    #lower_mask = marker_df['marker_id'] == 'Lower Marker'
    #upper_mask = marker_df['marker_id'] == 'Upper Marker'

    #lower_df = marker_df[lower_mask].copy()
    #upper_df = marker_df[upper_mask].copy()

    #sc_data_lower = ColumnDataSource(lower_df)
    #uc_data_lower = ColumnDataSource(lower_df)
    #sc_data_upper = ColumnDataSource(upper_df)

    #Plot the two's sizes vs 





    l = layout(
            [WidgetBox(readme)],
            [ts_data_multi_select],
            [conc_slider],
            [int_area_slider],
            [first_peak_plot, size_plot]
            )

    script, div_dict = components(l)
    return render_template('homepage.html', script=script, div=div_dict, bokeh_version=BOKEH_VERSION)



if __name__ == '__main__':
    #Set debug to False in a production environment
    app.run(port=5000, debug=True)
