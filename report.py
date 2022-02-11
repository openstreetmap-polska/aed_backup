import matplotlib.pyplot as plt
import pandas as pd

from datetime import datetime
from os.path import join
from typing import Any, Dict, List


REPORT_DIR = 'report_data'
DATE_FORMAT = '%Y-%m-%d'
DPI = 300

plt.rcParams['figure.figsize'] = (16, 8)
pd.set_option('display.max_columns', None)

current_date = datetime.now().date()
current_date_str = datetime.now().strftime(DATE_FORMAT)


def overpass_to_dataframe(overpass: dict) -> pd.DataFrame:
    data = []
    for elem in overpass['elements']:
        tags = elem['tags']
        del elem['tags']
        elem.update(tags)
        data.append(elem)

    return pd.json_normalize(data)


def total_aed_plot(df_date: pd.DataFrame) -> Dict[str, Any]:
    plt.clf()
    plt.plot(df_date['date'], df_date['sum'])
    plt.title(
        'Number of AEDs in the OpenStreetMap database in Poland'
        'from first edition, day by day.'
        f' As at: {current_date_str}',

        fontsize=14,
        loc='left'
    )
    filename = join(REPORT_DIR, 'total_aed.png')
    plt.savefig(filename, dpi=DPI)
    return {
        'heading': 'Total AED plot',
        'heading_level': 2,
        'content': f'![]({filename})'
    }


def current_year_aed_scatter_plot(
    df_date: pd.DataFrame,
    from_year: int
) -> Dict[str, Any]:
    df_date_curr_year = df_date.loc[df_date['year'] == from_year]

    plt.clf()
    plt.plot(df_date_curr_year['date'], df_date_curr_year['sum'])
    plt.scatter(
        df_date_curr_year['date'],
        df_date_curr_year['sum'],
        s=df_date_curr_year['changes'] * 10,
        alpha=0.3
    )
    from_dt_str = datetime(from_year, 1, 1).date().strftime(DATE_FORMAT)
    plt.title(
        'Number of AEDs in the OpenStreetMap database in Poland'
        f'from {from_dt_str}, day by day.'
        f'As at: {current_date_str}',

        fontsize=14,
        loc='left'
    )

    filename = join(REPORT_DIR, 'current_year_aed.png')
    plt.savefig(filename, dpi=DPI)

    return {
        'heading': 'Current year AED plot',
        'heading_level': 2,
        'content': f'![]({filename})'
    }


def top_editors(df: pd.DataFrame, top: int = 25) -> Dict[str, Any]:
    OSM_USER_URL = 'https://www.openstreetmap.org/user/'

    df_users = df['user'].value_counts(sort=True).reset_index()
    columns = ['User', 'Changesets']
    df_users.columns = columns
    df_users['user_link'] = OSM_USER_URL + df_users['User'].astype(str)

    md_content_table = [
        f'| # | {columns[0]} | {columns[1]} |',
        '| ------------- | ------------- | ------------- |'
    ]

    for index, row in df_users.head(top).iterrows():
        user = row[columns[0]]
        changesets = row[columns[1]]
        url = row['user_link']

        md_content_table.append(
            f'| {index + 1} | [{user}](<{url}>) | {changesets} |'
        )

    return {
        'heading': 'Top editors',
        'heading_level': 2,
        'content': '\n'.join(md_content_table)
    }


def tag_access_pie(df: pd.DataFrame) -> Dict[str, Any]:
    access_info = {
        'Atr': ['Access', 'No Data'],
        'Count': [
            len(df.index) - df['access'].isna().sum(),
            df['access'].isna().sum()
        ]
    }

    df2 = pd.DataFrame(access_info)
    plt.clf()
    plt.pie(df2['Count'], labels=df2['Atr'], autopct='%1.2f%%')
    plt.title(
        f'Defibrillators without introduced access method. ({current_date})',
        fontsize=14,
        loc='left'
    )

    filename = join(REPORT_DIR, 'tag_access.png')
    plt.savefig(filename, dpi=DPI)

    return {
        'heading': 'Tag access pie',
        'heading_level': 2,
        'content': f'![]({filename})'
    }


def tag_access_details_pie(df: pd.DataFrame) -> Dict[str, Any]:
    df_access = df['access'].value_counts(sort=True).reset_index()
    df_access.columns = ['Access', 'Value']
    df_access['Access2'] = (
        df_access['Access'] + '–' + df_access['Value'].astype(str) + ' pc.'
    )
    plt.clf()
    plt.pie(df_access['Value'], startangle=90)
    plt.title(f'Type of access ({current_date})', fontsize=14, loc='left')
    plt.legend(title='OSM access metods:', labels=df_access['Access2'])

    filename = join(REPORT_DIR, 'tag_access_details.png')
    plt.savefig(filename, dpi=DPI)

    return {
        'heading': 'Tag access details pie',
        'heading_level': 2,
        'content': f'![]({filename})'
    }


def tag_location_pie(df: pd.DataFrame) -> Dict[str, Any]:
    loc_info = {
        'Atr': ['Location', 'No Data'],
        'Count': [
            len(df.index) - df['defibrillator:location'].isna().sum(),
            df['defibrillator:location'].isna().sum()
        ]
    }
    df3 = pd.DataFrame(loc_info)
    plt.clf()
    plt.pie(df3['Count'], labels=df3['Atr'], autopct='%1.2f%%')
    plt.title(
        'Defibrillators without the location description entered '
        f'({current_date})',

        fontsize=14,
        loc='left'
    )
    filename = join(REPORT_DIR, 'tag_location.png')
    plt.savefig(filename, dpi=DPI)

    return {
        'heading': 'Tag location pie',
        'heading_level': 2,
        'content': f'![]({filename})'
    }


def simple_md_converter(data: List[Dict[str, Any]]) -> str:
    content = []
    for element in data:
        if type(element) != dict:
            continue

        content.append('{} {}\n{}\n'.format(
            '#' * element['heading_level'],
            element['heading'],
            element['content']
        ))

    return '\n'.join(content)


def create_report_md(overpass: Dict[Any, Any]) -> str:
    df = overpass_to_dataframe(overpass)

    # Initial data processing
    df.drop(['type'], axis='columns', inplace=True)
    df['year'] = pd.DatetimeIndex(df['timestamp']).year
    df['date'] = pd.DatetimeIndex(df['timestamp']).date

    df_date = df[['id', 'date']].groupby('date', as_index=False) \
                                .count() \
                                .rename(columns={'id': 'changes'})

    df_date['sum'] = df_date['changes'].cumsum()
    df_date['year'] = pd.DatetimeIndex(df_date['date']).year

    md = simple_md_converter([
        {'heading': 'AED backup and stats', 'heading_level': 1, 'content': ''},

        total_aed_plot(df_date),
        current_year_aed_scatter_plot(df_date, current_date.year),

        top_editors(df),

        tag_access_pie(df),
        tag_access_details_pie(df),
        tag_location_pie(df)
    ])

    return md

