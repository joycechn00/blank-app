import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt

st.title('HPLC Analysis')
uploaded_files = st.file_uploader("Upload HPLC files", accept_multiple_files = True)
HPLC_dicts = []
def parse(file):
    HPLC_dict = {}
    with open(file) as f:
        lines = f.readlines()
        is_peak_table = False
        for n,line in enumerate(lines):
            line_list = line.strip('\n').split('\t')
            if line_list[0]=='Sample Name':
                HPLC_dict['Sample Name'] = line_list[1]
            elif line_list[0]=='Sample ID':
                HPLC_dict['Sample ID'] = line_list[1]
            elif line_list[0]=='[Peak Table(Detector A-Ch1)]':
                is_peak_table = True
            elif is_peak_table and line_list[0]=='# of Peaks':
                HPLC_dict['# of Peaks'] = int(line_list[1])
                HPLC_dict['Peak Table Line'] = int(n)
                is_peak_table = False
            elif line_list[0]=='R.Time (min)':
                HPLC_dict['Chromatogram Line'] = int(n)
    return HPLC_dict
compiled_peaks = pd.DataFrame()
compiled_chrom = pd.DataFrame()
slope = None
y_int = None

##Dataframes
if uploaded_files!=[]:
    for file in uploaded_files:
        parsed_file = parse(file.name)
        parsed_file['Peak Table'] = pd.read_csv(file.name, skiprows = parsed_file['Peak Table Line']+1, nrows = parsed_file['# of Peaks'], sep = '\t')
        parsed_file['Peak Table'].insert(0,'Sample ID', parsed_file['Sample ID'])
        parsed_file['Peak Table'].insert(1,'Sample Name', parsed_file['Sample Name'])
        parsed_file['Chromatogram'] = pd.read_csv(file.name, skiprows = parsed_file['Chromatogram Line'], sep = '\t')
        parsed_file['Chromatogram'].insert(0,'Sample ID', parsed_file['Sample ID'])
        parsed_file['Chromatogram'].insert(1,'Sample Name', parsed_file['Sample Name'])
        HPLC_dicts.append(parsed_file)
    for entry in HPLC_dicts:
        compiled_peaks = pd.concat([compiled_peaks,entry['Peak Table']])
        compiled_chrom = pd.concat([compiled_chrom, entry['Chromatogram']])
    compiled_peaks = compiled_peaks[['Sample ID', 'Sample Name', 'Peak#', 'R.Time', 'Area']].reset_index(drop = True).drop_duplicates()
    sample_df = compiled_peaks[['Sample ID', 'Sample Name']]
    compiled_chrom = compiled_chrom[['Sample ID', 'Sample Name', 'R.Time (min)', 'Intensity']].drop_duplicates()
    

    ##App Layout
    ##User choose chromatogram or peak table
    st.header('Choose Visualization Method')
    filter = st.radio(label = 'Choices', options = ['Peak Table', 'Chromatograms'])

    ##Sidebar
    with st.sidebar:
        st.title('Edit Compiled Data')
        st.write("-------------------------------------------------------------------")
        ##User rename data
        rename = st.checkbox('Would you like to rename your samples?')
        st.caption('If unchecked, original sample names from HPLC files will be used for graphing and data processing.')
        if rename:
            st.header('Sample Renaming')
            st.write('Please rename samples for graphs and readability. Make sure to use unique names for each sample.')
            sample_df['New Sample Name'] = None
            rename_df = st.data_editor(sample_df, disabled = ('Sample Name'))
            compiled_peaks = compiled_peaks.merge(rename_df[['Sample Name', 'New Sample Name']], how = 'left', on = 'Sample Name')
            compiled_chrom = compiled_chrom.merge(rename_df[['Sample Name', 'New Sample Name']], how = 'left', on = 'Sample Name')
        else:
            rename_df = sample_df.rename(columns = {'Sample Name': 'New Sample Name'})
            compiled_peaks = compiled_peaks.rename(columns = {'Sample Name': 'New Sample Name'})
            compiled_chrom = compiled_chrom.rename(columns = {'Sample Name': 'New Sample Name'})

        st.write("-------------------------------------------------------------------")
        st.header('Standard Curve')
        options_std = ['Manual Input','Calculate Curve']
        select_std = st.selectbox('Standard Curve', options_std)

        if select_std == 'Manual Input':
            compiled_peaks['Input Concentrations'] = None
            slope = st.text_input ('Slope', value = None)
            y_int = st.text_input('y-intercept', value = None)
            scale = st.text_input('Scale', value = 'ug/mL')
        elif select_std == 'Calculate Curve':
            std_df = compiled_peaks
            std_df['Input Concentrations'] = None
            std_df = st.data_editor(std_df[['Sample ID','New Sample Name', 'Area','Input Concentrations']],disabled = ('Sample ID', 'New Sample Name','Area'))
            std_df_edited=std_df.dropna(axis = 0, how = 'any')
            if std_df_edited['Input Concentrations'].any():
                std_df_edited['Std Concentration'] = std_df_edited['Input Concentrations'].str.split(' ').str[0]
                scale = std_df_edited['Input Concentrations'].str.split(' ').str[1].iloc[0]
                fig = px.scatter(std_df_edited, x= 'Std Concentration', y = 'Area', trendline = 'ols')
                st.plotly_chart(fig)
                results = px.get_trendline_results(fig)
                slope = np.round(results.iloc[0]['px_fit_results'].params[1],1)
                y_int = np.round(results.iloc[0]['px_fit_results'].params[0],1)
            else:
                st.write("Please input concentrations with a space between number and units i.e., 5 ug/mL instead of 5ug/mL ")
    

        ##Show standard curve equation
        if select_std=='Manual Input' and slope is not None and y_int is not None:
            st.subheader('Standard Curve:')
            st.write('Area = '+slope+'[drug]+'+y_int)
        elif select_std=='Calculate Curve' and slope is not None and y_int is not None:
            st.subheader('Standard Curve:')
            st.write('Area = '+str(slope)+'[drug]+'+str(y_int))
            st.write(results.iloc[0]['px_fit_results'].summary())
        else:
            st.subheader('Standard Curve:')
        std_curve = st.button('Calculate Concentrations')
        st.write('Developed by Joyce Chen')
        st.caption('Woodrow Lab')

    if filter == 'Chromatograms':
        ##Chromatograms
        st.header('View Sample Chromatograms')
        options_chrom = rename_df['New Sample Name']
        select_chromatogram = st.multiselect('Select Chromatograms', options_chrom)
        if select_chromatogram == []:
            st.write("Please select samples to view.")
        else:
            for sample in select_chromatogram:
                sample_chrom = compiled_chrom[compiled_chrom['New Sample Name']==sample][['R.Time (min)', 'Intensity']]
                x = sample_chrom['R.Time (min)']
                y = sample_chrom['Intensity']
                fig, ax = plt.subplots()
                ax.plot(x,y)
                ax.set(xlabel = 'Retention Time', ylabel = 'Intensity', title = sample)
                fn = 'chromatogram'+sample+'.png'
                plt.savefig(fn)
                st.pyplot(fig)
                with open(fn, "rb") as img:
                    btn = st.download_button(
                        label="Download "+sample+" Chromatogram",
                        data=img,
                        file_name=fn,
                        mime="image/png"
                    )
    elif filter == 'Peak Table':
        compiled_peaks = compiled_peaks.drop(columns = ['Input Concentrations'])
        if std_curve:
            compiled_peaks['Calculated Concentration ('+scale+')'] = (compiled_peaks['Area']-int(y_int))/int(slope)
        st.header('Peak Data')
        st.dataframe(compiled_peaks)
        st.download_button(label = 'Download Peak Data', data = compiled_peaks.to_csv().encode("utf-8"), file_name = "compiled_data.csv")
else:
    st.write("Please upload HPLC files.")
