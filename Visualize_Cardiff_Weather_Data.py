import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from ladybug.epw import EPW, EPWFields
from ladybug.color import Colorset
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.legend import LegendParameters
from ladybug.hourlyplot import HourlyPlot
from ladybug.monthlychart import MonthlyChart
from ladybug.windrose import WindRose
from ladybug.psychchart import PsychrometricChart
from ladybug_charts.utils import Strategy
from ladybug_comfort.chart.polygonpmv import PolygonPMV
from ladybug_comfort.degreetime import heating_degree_time, cooling_degree_time
from ladybug.datatype.temperaturetime import HeatingDegreeTime, CoolingDegreeTime

st.set_page_config(page_title='Visualization of Cardiff Weather Data', layout="wide")
bgcolor = st.get_option("theme.backgroundColor")

# Customize the Streamlit UI: https://towardsdatascience.com/5-ways-to-customise-your-streamlit-ui-e914e458a17c
padding = 0
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)
    
def get_fields():
    # A dictionary of EPW variable name to its corresponding field number
    return {EPWFields._fields[i]['name'].name: i for i in range(6, 34)} # https://www.ladybug.tools/ladybug/docs/ladybug.epw.html#
fields = get_fields()

def get_figure_config(title: str):
    return {'toImageButtonOptions': {'format': 'png', # jpg, png, svg, webg
                                        'filename': title,
                                        'height': None,
                                        'width': None,
                                        'scale': 1}} # multiply title/legend/axis/canvas sizes by this factor

colorsets = {
    'Original': Colorset.original(),
    'Nuanced': Colorset.nuanced(),
    'Annual_comfort': Colorset.annual_comfort(),
    'Benefit': Colorset.benefit(),
    'Benefit_harm': Colorset.benefit_harm(),
    'Black_to_white': Colorset.black_to_white(),
    'Blue_green_red': Colorset.blue_green_red(),
    'Cloud_cover': Colorset.cloud_cover(),
    'Cold_sensation': Colorset.cold_sensation(),
    'Ecotect': Colorset.ecotect(),
    'Energy_balance': Colorset.energy_balance(),
    'Energy_balance_storage': Colorset.energy_balance_storage(),
    'Glare_study': Colorset.glare_study(),
    'Harm': Colorset.harm(),
    'Heat_sensation': Colorset.heat_sensation(),
    'Multi_colored': Colorset.multi_colored(),
    'Multicolored_2': Colorset.multicolored_2(),
    'Multicolored_3': Colorset.multicolored_3(),
    'Openstudio_palette': Colorset.openstudio_palette(),
    'Peak_load_balance': Colorset.peak_load_balance(),
    'Shade_benefit': Colorset.shade_benefit(),
    'Shade_benefit_harm': Colorset.shade_benefit_harm(),
    'Shade_harm': Colorset.shade_harm(),
    'Shadow_study': Colorset.shadow_study(),
    'Therm': Colorset.therm(),
    'Thermal_comfort': Colorset.thermal_comfort(),
    'View_study': Colorset.view_study()
}

####################################################################################################################
# Main Segment
####################################################################################################################
epw_path = 'EPW File/GBR_WAL_Cardiff.Wea.Ctr.037170_TMYx.epw'
global_epw = EPW(epw_path)


# ----------------------------------------------------------------- Part 1 Title and Header -----------------------------------------------------------------
with st.container():
    st.title(f'Visualization of Cardiff Weather Data')
    st.markdown('🙌 Welcome to the weather data visualization of city Cardiff, UK. Here you will get the full weather information of Cardiff. '
                '🖱️ Please use your cursor to hover over every charts to see the detail values and enjoy your exploration!')
    
    imageUrl = "https://unsplash.com/photos/qmZUcdwY5bE/download?ixid=MnwxMjA3fDB8MXxzZWFyY2h8Mnx8Y2FyZGlmZnxlbnwwfHx8fDE2ODI0MTA2Nzk&force=true&w=1920"
    st.image(image=imageUrl, use_column_width=True, caption="Cardiff Castle - URL: https://unsplash.com/photos/qmZUcdwY5bE")

# ----------------------------------------------------------------- Part 2 General Information -----------------------------------------------------------------
with st.container():
    st.header(f'General Information about Cardiff')   
    st.markdown("**Cardiff** is the capital and largest city of Wales. Cardiff had a population of 362,310 in 2021, forms a principal area officially known "
                "as the **City and County of Cardiff** (Welsh: Dinas a Sir Caerdydd), and the city is the eleventh-largest in the United Kingdom. "
                "In 2011, it ranked sixth in the world in a National Geographic magazine list of alternative tourist destinations. It is the most popular destination in Wales with 21.3 million visitors in 2017. _(Wikipedia)_")

    site_latitude = global_epw.location.latitude
    site_longitude = global_epw.location.longitude
    location = pd.DataFrame([np.array([site_latitude, site_longitude], dtype=np.float64)], columns=['latitude', 'longitude'])
    st.map(data=location, use_container_width=True, zoom=13)
    st.markdown(f'**City:** {global_epw.location.city}, **Latitude:** {site_latitude}, **Longitude:** {site_longitude}, **Timezone:** {global_epw.location.time_zone}, **Source:** {global_epw.location.source}')


# Thematic Break Line
st.markdown('---')


# ----------------------------------------------------------------- Part 3 EPW Charts -----------------------------------------------------------------
with st.container():
    st.header('Visualize Weather Data')
    global_colorset_selector = st.selectbox('Global Colorsets Selector for Charts', list(colorsets.keys()))
    color_switch = st.checkbox('Switch Colors', value=False, key='color_switch', help='Reverse the colorset')
    
    tabs = st.tabs(['Hourly Data', 'Daily Data', 'Monthly Data', 'Degree Days', 'Windrose', 'Psychrometric Chart'])
    
    dashed_line_style = """
    border-top: 1.2px dashed #999;
    width: 100%;
    margin: 60px auto;
    """
    
    def get_colors(switch: bool, global_colorset: str):
        if switch:
            colors = list(colorsets[global_colorset])
            colors.reverse()
        else:
            colors = colorsets[global_colorset]
        return colors
    

# Hourly Data ---------            
    with tabs[0]:
        st.subheader('Hourly Data Heatmap')
        st.markdown('Choose an environmental variable from the EPW weather file to display. By default, the hourly data is set to **Dry Bulb Temperature**. You can apply a conditional statement to filter the data. '
                    'For instance, use "a>10", without quotes, to display temperatures above 10, or "a>-5 and a<10", without quotes, for temperatures between -5 and 10. You can also adjust the min and max inputs to customize the data bounds and legend. '
                    'The chart automatically sets the bounds to the minimum and maximum values of the data by default.')

        def get_hourly_data_figure(data: HourlyContinuousCollection, global_colorset: str, conditional_statement: str, min: float, max: float, start_month: int, start_day: int, start_hour: int, 
                                   end_month: int, end_day: int, end_hour: int, switch: bool):
            lb_ap = AnalysisPeriod(start_month, start_day, start_hour, end_month, end_day, end_hour) # Create an Analysis Period to describe a slice of time during the year.
            filtered_data = data.filter_by_analysis_period(lb_ap)
            
            if conditional_statement:
                try:
                    filtered_data = data.filter_by_conditional_statement(conditional_statement)
                except AssertionError:
                    return 'No values found for that conditonal statement'
                except ValueError:
                    return 'Invalid conditonal statement'
            
            if min:
                try:
                    min = float(min)
                except ValueError:
                    return 'Invalid minimum value'
                
            if max:
                try:
                    max = float(max)
                except ValueError:
                    return 'Invalid maximum value'
            
            colors = get_colors(switch, global_colorset)
            lb_lp = LegendParameters(colors=colors)
            
            if min:
                lb_lp.min = min
            if max:
                lb_lp.max = max
                
            hourly_plot = HourlyPlot(data_collection=filtered_data, legend_parameters=lb_lp)
            return hourly_plot.plot(title=str(filtered_data.header.data_type), show_title=True)

        with st.expander('Control Panel', expanded=True):
            hourly_selected = st.selectbox(label='Select an environmental variable: ', options=fields.keys(), key='hourly_data')
            hourly_data = global_epw._get_data_by_field(fields[hourly_selected])
            col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
            with col1:
                hourly_data_conditonal_statement = st.text_input('Conditional statement: ')
            with col2:
                hourly_data_min = st.text_input('Min: ')
            with col3:
                hourly_data_max = st.text_input('Max: ')
            with col4:
                hourly_data_start_month = st.number_input('Start month: ', min_value=1, max_value=12, value=1, key='hourly_data_start_month')
            with col5:
                hourly_data_end_month = st.number_input('End month: ', min_value=1, max_value=12, value=12, key='hourly_data_end_month')
            with col6:
                hourly_data_start_day = st.number_input('Start day: ', min_value=1, max_value=31, value=1, key='hourly_data_start_day')
            with col7:
                hourly_data_end_day = st.number_input('End day: ', min_value=1, max_value=31, value=31, key='hourly_data_end_day')
            with col8:
                hourly_data_start_hour = st.number_input('Start hour: ', min_value=0, max_value=23, value=0, key='hourly_data_start_hour')
            with col9:
                hourly_data_end_hour = st.number_input('End hour: ', min_value=0, max_value=23, value=23, key='hourly_data_end_hour')
        
        hourly_data_figure = get_hourly_data_figure(
                                                    data=hourly_data, 
                                                    global_colorset=global_colorset_selector, 
                                                    conditional_statement=hourly_data_conditonal_statement, 
                                                    min=hourly_data_min, 
                                                    max=hourly_data_max, 
                                                    start_month=hourly_data_start_month, 
                                                    end_month=hourly_data_end_month, 
                                                    start_day=hourly_data_start_day, 
                                                    end_day=hourly_data_end_day, 
                                                    start_hour=hourly_data_start_hour, 
                                                    end_hour=hourly_data_end_hour,
                                                    switch=color_switch,
                                                    )
        
        hourly_data_figure.update_layout(title=dict(x=0.5, y=0.96), margin=dict(t=60, b=0, pad=0), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(hourly_data_figure, use_container_width=True, config=get_figure_config(f'{hourly_data.header.data_type}'))
           

        
# Daily Data ---------        
    with tabs[1]: 
        st.subheader('Hourly Line Chart')
        st.markdown('Choose an environmental variable from the EPW weather file to display on a line chart. By default, the hourly data is set to **Dry Bulb Temperature**.')
        
        with st.expander('Control Panel', expanded=True):
            daily_data_selected = st.selectbox(label='Select an environmental variable: ', options=fields.keys(), index=0, key='daily_data_line_chart_and_bar_chart')
            daily_data_chart_data = global_epw._get_data_by_field(fields[daily_data_selected])
        
        def get_hourly_line_chart_figure(data: HourlyContinuousCollection, switch: bool, global_colorset: str, selection: str):
            colors = get_colors(switch, global_colorset)
            return data.line_chart(color=colors[9], title=selection, show_title=True)
            
        hourly_line_chart_figure = get_hourly_line_chart_figure(daily_data_chart_data, color_switch, global_colorset_selector, daily_data_selected)
        hourly_line_chart_figure.update_layout(margin=dict(t=96, b=0, pad=0), title=dict(x=0.5, y=0.96), legend=dict(bgcolor='rgba(0, 0, 0, 0)'), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(hourly_line_chart_figure, use_container_width=True, config=get_figure_config(f'{daily_data_selected}'))


        # Thematic Break Line
        st.markdown(f'<div style="{dashed_line_style}"></div>', unsafe_allow_html=True)


        st.subheader('Daily Chart')
        st.markdown('Choose an environmental variable from the EPW weather file to display on a daily chart, which presents average daily values. By default, the hourly data is set to **Dry Bulb Temperature**.')
    
        def get_daily_chart_figure(data: HourlyContinuousCollection, switch: bool, global_colorset: str):
            colors = get_colors(switch, global_colorset)
            data = data.average_daily()
            return data.bar_chart(color=colors[9], title=data.header.data_type.name, show_title=True)
        
        daily_chart_figure = get_daily_chart_figure(daily_data_chart_data, color_switch, global_colorset_selector)
        daily_chart_figure.update_layout(margin=dict(t=60, b=0, pad=0), title=dict(x=0.5, y=0.96), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(daily_chart_figure, use_container_width=True, config=get_figure_config(f'{daily_data_chart_data.header.data_type.name}'))        
                  


# Monthly Data ---------    
    with tabs[2]: 
        st.subheader('Diurnal Average Chart')
        st.markdown('A chart illustrating the typical weather for each month, based on daily averages.')
        
        def get_diurnal_average_chart_figure(epw: EPW, global_colorset: str, switch: bool=False):
            colors = get_colors(switch, global_colorset)
            return epw.diurnal_average_chart(show_title=True, colors=colors)
        
        diurnal_average_chart_figure = get_diurnal_average_chart_figure(global_epw, global_colorset_selector, color_switch)
        diurnal_average_chart_figure.update_layout(title=dict(x=0.5, y=0.96), margin=dict(t=96, b=54, pad=5), legend=dict(x=1, y=1.05, orientation='h', bgcolor='rgba(0, 0, 0, 0)'), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(diurnal_average_chart_figure, use_container_width=True, config=get_figure_config(f'Dinurnal Chart_{global_epw.location.city}'))


        # Thematic Break Line
        st.markdown(f'<div style="{dashed_line_style}"></div>', unsafe_allow_html=True)


        st.subheader('Diurnal Average Chart (Hourly Data)')
        st.markdown('Choose an environmental variable from the EPW weather file to display on a diurnal average chart. By default, the hourly data is set to **Dry Bulb Temperature**.')

        with st.expander('Control Panel', expanded=True):
            diurnal_average_chart_hourly_selected = st.selectbox('Select an environmental variable: ', options=fields.keys(), index=0, key='hourly_diurnal_average_chart')
            diurnal_average_chart_hourly_data = global_epw._get_data_by_field(fields[diurnal_average_chart_hourly_selected])

        def get_hourly_diurnal_average_chart_figure(data: HourlyContinuousCollection, switch: bool, global_colorset: str):
            colors = get_colors(switch, global_colorset)
            return data.diurnal_average_chart(title=data.header.data_type.name, show_title=True, color=colors[9])
        
        per_hour_line_chart_figure = get_hourly_diurnal_average_chart_figure(diurnal_average_chart_hourly_data, color_switch, global_colorset_selector)
        per_hour_line_chart_figure.update_layout(margin=dict(t=60, b=54, pad=5), title=dict(x=0.5, y=0.96), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(per_hour_line_chart_figure, use_container_width=True, config=get_figure_config(f'{diurnal_average_chart_hourly_data.header.data_type.name}'))
        
        
        # Thematic Break Line
        st.markdown(f'<div style="{dashed_line_style}"></div>', unsafe_allow_html=True)        


        st.subheader('Bar Chart')
        st.markdown('Choose one or more environmental variables from the EPW weather file to display on a monthly bar chart side by side. By default, **Dry Bulb Temperature** and **Dew Point Temperature** are selected.')       
        
        
        bar_chart_selection = []
        keys = list(fields.keys())
        with st.expander('Control Panel', expanded=True):
            col_a = st.columns(7)
            for i, var1 in enumerate(keys[0:7]):
                with col_a[i]:
                    if var1 == 'Dry Bulb Temperature' or var1 == 'Dew Point Temperature':
                        bar_chart_selection.append(st.checkbox(var1, value=True, key=var1))
                    else:
                        bar_chart_selection.append(st.checkbox(var1, value=False, key=var1))

            col_b = st.columns(7)
            for j, var2 in enumerate(keys[7:14]):
                with col_b[j]:
                    if var2 == 'Dry Bulb Temperature' or var2 == 'Dew Point Temperature':
                        bar_chart_selection.append(st.checkbox(var2, value=True, key=var2))
                    else:
                        bar_chart_selection.append(st.checkbox(var2, value=False, key=var2))
            
            col_c = st.columns(7)
            for k, var3 in enumerate(keys[14:21]):
                with col_c[k]:
                    if var3 == 'Dry Bulb Temperature' or var3 == 'Dew Point Temperature':
                        bar_chart_selection.append(st.checkbox(var3, value=True, key=var3))
                    else:
                        bar_chart_selection.append(st.checkbox(var3, value=False, key=var3))
                
            col_d = st.columns(7)
            for l, var4 in enumerate(keys[21:28]):
                with col_d[l]:
                    if var4 == 'Dry Bulb Temperature' or var4 == 'Dew Point Temperature':
                        bar_chart_selection.append(st.checkbox(var4, value=True, key=var4))
                    else:
                        bar_chart_selection.append(st.checkbox(var4, value=False, key=var4))
            
                            
            bar_chart_data_type = st.selectbox(label='Select a data type: ', options=('Monthly Average', 'Monthly Total'))
            bar_chart_stack = st.checkbox('Stack', value=False, key='bar_chart_stacked')
        
        def get_bar_chart_figure(fields: dict, epw: EPW, selection: list, data_type: str, switch: bool, stack: bool, global_colorset: str):
            colors = get_colors(switch, global_colorset)
            
            data = []
            for i, item in enumerate(selection):
                if item:
                    var = epw._get_data_by_field(fields[list(fields.keys())[i]])
                    if data_type == 'Monthly Average':
                        data.append(var.average_monthly())
                    elif data_type == 'Monthly Total':
                        data.append(var.total_monthly())
            
            lb_lp = LegendParameters(colors=colors)
            monthly_chart = MonthlyChart(data, legend_parameters=lb_lp, stack=stack)
            return monthly_chart.plot()
            
        bar_chart_figure = get_bar_chart_figure(fields, global_epw, bar_chart_selection, bar_chart_data_type, color_switch, bar_chart_stack, global_colorset_selector)
        if bar_chart_selection.count(True) == 1:
            bar_chart_figure.update_layout(margin=dict(t=30, b=0, pad=0), title=dict(text='', x=0.5, y=0.96), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        else:
            bar_chart_figure.update_layout(margin=dict(t=30, b=0, pad=0), legend=dict(x=0, y=1.1, orientation='h', bgcolor='rgba(0, 0, 0, 0)'), yaxis_title=None, title=dict(text='', x=0.5, y=0.96), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        bar_chart_figure.update_traces(marker=dict(line=dict(width=0)))
        st.plotly_chart(bar_chart_figure, use_container_width=True, config=get_figure_config(f'{bar_chart_data_type}'))



# Degree Days ---------            
    with tabs[3]:
        st.subheader('Degree Days')
        st.markdown('Computes heating and cooling degree-days, which are traditionally defined as the difference between a base temperature and the average ambient air temperature, '
                    'multiplied by the number of days this difference occurs. The default base temperatures for heating and cooling are 18°C and 23°C, respectively. This implies that heating is deployed below the heating base temperature, while cooling is deployed above the cooling base temperature.')    
        
        with st.expander('Control Panel', expanded=True):
            degree_days_heat_base = st.number_input(label='Base heating temperature: ', value=18)
            degree_days_cool_base = st.number_input(label='Base cooling temperature: ', value=23)
            degree_days_stack = st.checkbox('Stack')
        
        def get_degree_days_figure(data: HourlyContinuousCollection, heatbase: int, coolbase: int, stack: bool, switch: bool, global_colorset: str):
            hourly_heat = HourlyContinuousCollection.compute_function_aligned(heating_degree_time, [data, heatbase], HeatingDegreeTime(), unit='degC-hours')
            hourly_heat.convert_to_unit('degC-days')
            hourly_cool = HourlyContinuousCollection.compute_function_aligned(cooling_degree_time, [data, coolbase], CoolingDegreeTime(), unit='degC-hours')
            hourly_cool.convert_to_unit('degC-days')
            
            colors = get_colors(switch, global_colorset)
            
            lb_lp = LegendParameters(colors=colors)
            monthly_chart = MonthlyChart([hourly_cool.total_monthly(), hourly_heat.total_monthly()], legend_parameters=lb_lp, stack=stack)
            return monthly_chart.plot(), hourly_heat, hourly_cool
        
        degree_days_figure, hourly_heat, hourly_cool = get_degree_days_figure(global_epw.dry_bulb_temperature, degree_days_heat_base, degree_days_cool_base, degree_days_stack, color_switch, global_colorset_selector)
        degree_days_figure.update_layout(margin=dict(pad=0), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor, title='')
        degree_days_figure.update_traces(marker=dict(line=dict(width=0)))
        st.plotly_chart(degree_days_figure, use_container_width=True, config=get_figure_config(f'Degree days_{global_epw.location.city}'))
        st.markdown(f'**Total Cooling Degree Days** are **:blue[{round(hourly_cool.total)}]** and **Total Heating Degree Days** are **:red[{round(hourly_heat.total)}]**.')
        
        

# Wind Rose ---------            
    with tabs[4]:
        st.subheader('Windrose')
        st.markdown('A windrose diagram that displays the distribution of wind speed and direction at Cardiff.')
        
        with st.expander('Control Panel', expanded=True):
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                windrose_start_month = st.number_input('Start month: ', min_value=1, max_value=12, value=1, key='windrose_start_month')
            with col2:
                windrose_end_month = st.number_input('End month: ', min_value=1, max_value=12, value=12, key='windrose_end_month')
            with col3:
                windrose_start_day = st.number_input('Start day: ', min_value=1, max_value=31, value=1, key='windrose_start_day')
            with col4:
                windrose_end_day = st.number_input('End day: ', min_value=1, max_value=31, value=31, key='windrose_end_day')
            with col5:
                windrose_start_hour = st.number_input('Start hour: ', min_value=0, max_value=23, value=0, key='windrose_start_hour')
            with col6:
                windrose_end_hour = st.number_input('End hour: ', min_value=0, max_value=23, value=23, key='windrose_end_hour')
            
        def get_windrose_figure(start_month: int, end_month: int, start_day: int, end_day: int, start_hour: int, end_hour: int, epw: EPW, global_colorset: str, switch: bool):
            colors = get_colors(switch, global_colorset)
            lb_ap = AnalysisPeriod(start_month, start_day, start_hour, end_month, end_day, end_hour)
            wind_dir = epw.wind_direction.filter_by_analysis_period(lb_ap)
            wind_spd = epw.wind_speed.filter_by_analysis_period(lb_ap)
            
            lb_lp = LegendParameters(colors=colors)
            lb_wind_rose = WindRose(wind_dir, wind_spd)
            lb_wind_rose.legend_parameters = lb_lp
            return lb_wind_rose.plot(title=f'{global_epw.location.city}, {global_epw.location.country}', show_title=True)
            
        windrose_figure = get_windrose_figure(windrose_start_month, windrose_end_month, windrose_start_day, windrose_end_day, windrose_start_hour, windrose_end_hour, global_epw, global_colorset_selector, color_switch)
        windrose_figure.update_layout(margin=dict(t=60, b=0, pad=0), title=dict(x=0.46, y=0.96), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor)
        st.plotly_chart(windrose_figure, use_container_width=True, config=get_figure_config(f'Windrose_{global_epw.location.city}'))
        
        

# Psychrometric Chart ---------            
    with tabs[5]:
        st.subheader('Psychrometric Chart')
        st.markdown('Generate a psychrometric chart for the **Dry Bulb Temperature** and **Relative Humidity** from the weather file. You can also load one of the environmental variables of EPW on the psychrometric chart. ' 
                    'Additionally, you can add comfort polygons to the chart by selecting one of the passive strategies. By default, the psychrometric chart displays the annual occurrence of specific dry bulb temperatures and relative humidity levels.')
        
        with st.expander('Control Panel', expanded=True):
            psy_load_data = st.checkbox(label='Load data', key='Psychrometric_load_data')
            if psy_load_data:
                psy_selected = st.selectbox(label='Select an environmental variable: ', options=fields.keys(), key='Psychrometric_selected')
                psy_data = global_epw._get_data_by_field(fields[psy_selected])
            else:
                psy_data = None
            
            psy_draw_polygons = st.checkbox(label='Draw comfort polygons', key='Psychrometric_draw_polygons')
            psy_strategy_options = ['Mass + Night Ventilation', 'Occupant Use of Fans', 'Capture Internal Heat', 'Passive Solar Heating', 'All']
            psy_selected_strategy = st.selectbox(label='Select a passive strategy (Please remember to check the "Draw comfort polygons" option to see the result): ', options=psy_strategy_options, key='Psychrometric_selected_strategy')
            
        # https://docs.ladybug.tools/ladybug-primer/components/4_extra/passive_strategy_parameters
        passive_strategy_explanation = [['The polygon represents the conditions under which shaded, night-flushed thermal mass can keep occupants cool. By default, this polygon assumes that temperatures can get as high as 12 C above the max temperature of the comfort polygon as long temperatures 8 hours before the hot hour are 3.0 C lower than the max temperture of the comfort polygon. This parameter component can be used to adjust these two temperature values and the number of hours that the building keeps its "coolth".'], 
                                        ['The polygon is made by assuming that an air speed of 1.0 m/s is the maximum speed tolerable before papers start blowing around and conditions become annoying to occupants. The polygon is determined by running a PMV model with this fan air speed and the PMV inputs of the warmest comfort conditions. This parameter component can be used to adjust this maximum acceptable air speed.'], 
                                        ['The polygon is made by assuming a minimum building balance point of 12.8 C and any conditions that are warmer than that will keep occupants comfortable (up to the comfort polygon). It is assumed that, above this building balance temperature, the building is free-running and occupants are able to open windows as they wish to keep conditions from overshooting the comfort polygon. Note that the default balance temperature of 12.8 C is fairly low and assumes a significant amount of internal heat from people, equipment. etc. Or the building as a well-insulated envelope to ensure what internal heat there is can leave the building slowly. This parameter component can be used to adjust the balance temperature.'], 
                                        ['The polygon represents the conditions under which sun-exposed thermal mass can keep occupants warm in winter. By default, this polygon assumes that temperatures can get as high as 12 C above the max temperature of the comfort polygon as long temperatures 8 hours before the hot hour are 3.0 C lower than the max temperture of the comfort polygon. This parameter component can be used to adjust these two temperature values and the number of hours that the building keeps its "coolth".']]
        df_passive_strategy_explanation = pd.DataFrame(data=passive_strategy_explanation, index=psy_strategy_options[0:-1], columns=['Explanation'])
        with st.expander('Passive Strategy Explanation'):
            st.table(df_passive_strategy_explanation)
        
        def get_psy_chart_figure(epw: EPW, global_colorset: str, selected_strategy: str, load_data: bool, draw_polygons: bool, data: HourlyContinuousCollection, switch: bool):
            colors = get_colors(switch, global_colorset)
            lb_lp = LegendParameters(colors=colors)
            lb_psy = PsychrometricChart(epw.dry_bulb_temperature, epw.relative_humidity, legend_parameters=lb_lp)
            
            if selected_strategy == 'All':
                strategies = [Strategy.comfort, Strategy.evaporative_cooling, Strategy.mas_night_ventilation, Strategy.occupant_use_of_fans, Strategy.capture_internal_heat, Strategy.passive_solar_heating]
            elif selected_strategy == 'Comfort':
                strategies = [Strategy.comfort]
            elif selected_strategy == 'Evaporative Cooling':
                strategies = [Strategy.evaporative_cooling]
            elif selected_strategy == 'Mass + Night Ventilation':
                strategies = [Strategy.mas_night_ventilation]
            elif selected_strategy == 'Occupant Use of Fans':
                strategies = [Strategy.occupant_use_of_fans]
            elif selected_strategy == 'Capture Internal Heat':
                strategies = [Strategy.capture_internal_heat]
            elif selected_strategy == 'Passive Solar Heating':
                strategies = [Strategy.passive_solar_heating]
            
            pmv = PolygonPMV(lb_psy)
            
            if load_data:
                if draw_polygons:
                    fig = lb_psy.plot(data=data, polygon_pmv=pmv, strategies=strategies, solar_data=epw.direct_normal_radiation)
                else:
                    fig = lb_psy.plot(data=data)
            else:
                if draw_polygons:
                    fig = lb_psy.plot(polygon_pmv=pmv, strategies=strategies, solar_data=epw.direct_normal_radiation)
                else:
                    fig = lb_psy.plot()
                    
            return fig
        
        psy_chart_figure = get_psy_chart_figure(global_epw, global_colorset_selector, psy_selected_strategy, psy_load_data, psy_draw_polygons, psy_data, color_switch)
        psy_chart_figure.update_layout(margin=dict(pad=0), plot_bgcolor=bgcolor, paper_bgcolor=bgcolor, title='')
        st.plotly_chart(psy_chart_figure, use_container_width=True, config=get_figure_config(f'Psychrometric_chart_{global_epw.location.city}'))
        


            
# ----------------------------------------------------------------- Part 4 Terms Explanations -----------------------------------------------------------------
 # Thematic Break Line
st.markdown('---')

with st.container(): # https://www.ladybug.tools/ladybug/docs/ladybug.epw.html
    term_explanation = [['This is the Dry Bulb Temperature in C at the time indicated. (The temperature of air measured by a thermometer that is not affected by the moisture of the air. It is also called "air temperature" or "ambient air temperature"). Note that this is a full numeric field (i.e. 23.6) and not an integer representation with tenths. Valid values range from -70C to 70C. Missing value for this field is 99.9.'],
                        ['This is the Dew Point Temperature in C at the time indicated. (The temperature at which air becomes saturated with water vapor, assuming constant air pressure and water content. The higher the dew point temperature, the more humid the air is). Note that this is a full numeric field (i.e. 23.6) and not an integer representation with tenths. Valid values range from -70C to 70C. Missing value for this field is 99.9.'],
                        ['This is the Relative Humidity in percent at the time indicated. (The ratio of how much water vapour is in the air and how much water vapour the air could potentially contain at a given temperature). Valid values range from 0% to 110%. Missing value for this field is 999.'],
                        ['This is the Station Pressure in Pa at the time indicated. (Also known as "barometric pressure" (after the barometer), is the pressure within the atmosphere of Earth). Valid values range from 31,000 to 120,000. (These values were chosen from the standard barometric pressure for all elevations of the World). Missing value for this field is 999999.'],
                        ['This is the Extraterrestrial Horizontal Radiation in Wh/m2. (Amount of solar energy per unit time received on a unit area of a horizontal surface outside the atmosphere). It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 9999.'],
                        ['This is the Extraterrestrial Direct Normal Radiation in Wh/m2. (Amount of solar radiation in Wh/m2 received on a surface normal to the rays of the sun at the top of the atmosphere during the number of minutes preceding the time indicated). It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 9999.'], 
                        ['This is the Horizontal Infrared Radiation Intensity in W/m2. (Defined as the rate of infrared radiation emitted from the sky falling on a horizontal upward-facing surface). If it is missing, it is calculated from the Opaque Sky Cover field as shown in the following explanation. It should have a minimum value of 0; missing value for this field is 9999.'], 
                        ['This is the Global Horizontal Radiation in Wh/m2. (Total amount of direct and diffuse solar radiation in Wh/m2 received on a horizontal surface during the number of minutes preceding the time indicated.) It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 9999.'], 
                        ["This is the Direct Normal Radiation in Wh/m2. (Amount of solar radiation in Wh/m2 received directly from the solar disk on a surface perpendicular to the sun's rays, during the number of minutes preceding the time indicated.) If the field is missing ( >= 9999) or invalid ( < 0), it is set to 0. Counts of such missing values are totaled and presented at the end of the runperiod."], 
                        ["This is the Diffuse Horizontal Radiation in Wh/m2. (Amount of solar radiation in Wh/m2 received from the sky (excluding the solar disk) on a horizontal surface during the number of minutes preceding the time indicated.) If the field is missing ( >= 9999) or invalid ( < 0), it is set to 0. Counts of such missing values are totaled and presented at the end of the runperiod."], 
                        ["This is the Global Horizontal Illuminance in lux. (Average total amount of direct and diffuse illuminance in hundreds of lux received on a horizontal surface during the number of minutes preceding the time indicated.) It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 999999 and will be considered missing if greater than or equal to 999900."], 
                        ["This is the Direct Normal Illuminance in lux. (Average amount of illuminance in hundreds of lux received directly from the solar disk on a surface perpendicular to the sun's rays, during the number of minutes preceding the time indicated.) It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 999999 and will be considered missing if greater than or equal to 999900."], 
                        ['This is the Diffuse Horizontal Illuminance in lux. (Average amount of illuminance in hundreds of lux received from the sky (excluding the solar disk) on a horizontal surface during the number of minutes preceding the time indicated.) It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 999999 and will be considered missing if greater than or equal to 999900.'], 
                        ["This is the Zenith Illuminance in Cd/m2. (Average amount of luminance at the sky's zenith in tens of Cd/m2 during the number of minutes preceding the time indicated.) It is not currently used in EnergyPlus calculations. It should have a minimum value of 0; missing value for this field is 9999."], 
                        ['This is the Wind Direction in degrees where the convention is that North=0.0, East=90.0, South=180.0, West=270.0. (Wind direction in degrees at the time indicated. If calm, direction equals zero.) Values can range from 0 to 360. Missing value is 999.'], 
                        ['This is the wind speed in m/sec. (Wind speed at time indicated.) Values can range from 0 to 40. Missing value is 999.'], 
                        ['This is the value for total sky cover (tenths of coverage). (i.e. 1 is 1/10 covered. 10 is total coverage). (Amount of sky dome in tenths covered by clouds or obscuring phenomena at the hour indicated at the time indicated.) Minimum value is 0; maximum value is 10; missing value is 99.'], 
                        ['This is the value for opaque sky cover (tenths of coverage). (i.e. 1 is 1/10 covered. 10 is total coverage). (Amount of sky dome in tenths covered by clouds or obscuring phenomena that prevent observing the sky or higher cloud layers at the time indicated.) This is not used unless the field for Horizontal Infrared Radiation Intensity is missing and then it is used to calculate Horizontal Infrared Radiation Intensity. Minimum value is 0; maximum value is 10; missing value is 99.'], 
                        ['This is the value for visibility in km. (Horizontal visibility at the time indicated.) It is not currently used in EnergyPlus calculations. Missing value is 9999.'], 
                        ['This is the value for ceiling height in m. (77777 is unlimited ceiling height. 88888 is cirroform ceiling.) It is not currently used in EnergyPlus calculations. Missing value is 99999.'], 
                        ['If the value of the field is 0, then the observed weather codes are taken from the following field. If the value of the field is 9, then “missing” weather is assumed. Since the primary use of these fields (Present Weather Observation and Present Weather Codes) is for rain/wet surfaces, a missing observation field or a missing weather code implies no rain.'], 
                        ['The Present Weather Codes field is assumed to follow the TMY2 conventions for this field. Note that though this field may be represented as numeric (e.g. in the CSV format), it is really a text field of 9 single digits. This convention along with values for each “column” (left to right) is presented in Table 16. Note that some formats (e.g. TMY) does not follow this convention - as much as possible, the present weather codes are converted to this convention during WeatherConverter processing. Also note that the most important fields are those representing liquid precipitation - where the surfaces of the building would be wet. EnergyPlus uses “Snow Depth” to determine if snow is on the ground.'], 
                        ['This is the value for Precipitable Water in mm. (This is not rain - rain is inferred from the PresWeathObs field but a better result is from the Liquid Precipitation Depth field). It is not currently used in EnergyPlus calculations (primarily due to the unreliability of the reporting of this value). Missing value is 999.'], 
                        ['This is the value for Aerosol Optical Depth in thousandths. It is not currently used in EnergyPlus calculations. Missing value is .999.'], 
                        ['This is the value for Snow Depth in cm. This field is used to tell when snow is on the ground and, thus, the ground reflectance may change. Missing value is 999.'], 
                        ['This is the value for Days Since Last Snowfall. It is not currently used in EnergyPlus calculations. Missing value is 99.'], 
                        ['The ratio (unitless) of reflected solar irradiance to global horizontal irradiance. It is not currently used in EnergyPlus.'], 
                        ['The amount of liquid precipitation (mm) observed at the indicated time for the period indicated in the liquid precipitation quantity field. If this value is not missing, then it is used and overrides the “precipitation” flag as rainfall. Conversely, if the precipitation flag shows rain and this field is missing or zero, it is set to 1.5 (mm).']]
    df_term_explanation = pd.DataFrame(data=term_explanation, index=fields.keys(), columns=['Explanation (Annual Basis)'])
    st.header('Terminology')
    st.table(df_term_explanation)
        

    
    
    
    
