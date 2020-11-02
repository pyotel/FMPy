import os
import flask
import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import fmpy
from dash.dependencies import Input, Output, State
from fmpy import read_model_description, simulate_fmu, extract
from fmpy.util import create_plotly_figure
import argparse

parser = argparse.ArgumentParser(description="Run the FMPy WebApp")

parser.add_argument('fmu_filename', help="Filename of the FMU")
parser.add_argument('--host', default='127.0.0.1', help="Host IP used to serve the application")
parser.add_argument('--port', default='8050', type=int, help="Port used to serve the application")
parser.add_argument('--debug', action='store_true', help="Set Flask debug mode and enable dev tools")

args = parser.parse_args()

unzipdir = extract(args.fmu_filename)

print('Extracting FMU to %s' % unzipdir)

model_description = read_model_description(unzipdir)

# server = flask.Flask(__name__)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP]) #, server=server)

app.title = model_description.modelName

names = []
rows = []
states = []

for i, variable in enumerate(model_description.modelVariables):

    if variable.causality == 'parameter':

        unit = variable.unit

        if unit is None and variable.declaredType is not None:
            unit = variable.declaredType.unit

        names.append(variable.name)

        id = f'variable-{i}'

        row = dbc.FormGroup(
            [
                dbc.Label(variable.name, html_for=id, width=6),
                dbc.Col(
                    dbc.InputGroup(
                        [
                            dbc.Input(id=id, value=variable.start, style={'text-align': 'right'}),
                            dbc.InputGroupAddon(unit if unit else ' ', addon_type='append'),
                        ], size="sm"
                    ),
                    width=6,
                ),
            ],
            row=True,
            className='mb-2'
        )

        rows.append(row)

        states.append(State(id, 'value'))

stop_time = None

if model_description.defaultExperiment:
    stop_time = model_description.defaultExperiment.stopTime

if stop_time is None:
    stop_time = '1'

fmi_types = []

if model_description.modelExchange:
    fmi_types.append('Model Exchange')

if model_description.coSimulation:
    fmi_types.append('Co-Simulation')

app.layout = dbc.Container([

    dbc.Tabs(
        [
            dbc.Tab(label="Model Info", tab_id="model-info-tab"),
            dbc.Tab(label="Simulation", tab_id="simulation-tab"),
            dbc.Tab(label="Documentation", tab_id="documentation-tab"),
        ],
        className='pt-4 mb-4',
        active_tab="simulation-tab",
        id='tabs'
    ),

    dbc.Container(
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Row([
                            dbc.Col(html.Span("FMI Version"), width=4),
                            dbc.Col(html.Span(model_description.fmiVersion), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col("FMI Type", width=4),
                            dbc.Col(', '.join(fmi_types), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Continuous States"), width=4),
                            dbc.Col(html.Span(model_description.numberOfContinuousStates), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Event Indicators"), width=4),
                            dbc.Col(html.Span(model_description.numberOfEventIndicators), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Variables"), width=4),
                            dbc.Col(html.Span(len(model_description.modelVariables)), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Generation Date"), width=4),
                            dbc.Col(html.Span(model_description.generationDateAndTime), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Generation Tool"), width=4),
                            dbc.Col(html.Span(model_description.generationTool), width=8),
                        ], className='py-1'),
                        dbc.Row([
                            dbc.Col(html.Span("Description"), width=4),
                            dbc.Col(html.Span(model_description.description), width=8),
                        ], className='py-1'),
                    ], width=8
                ),
                dbc.Col(
                    [
                        html.Img(src="/model.png", className='img-fluid')
                    ], width=4
                ),
            ]
        ),
        id='model-info-container',
    ),

    dbc.Container(
        [
            dbc.Form(
                [
                    dbc.Button('Simulate', id='simulate-button', color='primary', className='mr-4'),
                    dbc.InputGroup(
                        [
                            dbc.Input(id="stop-time", value=stop_time, style={'width': '4em'}),
                            dbc.InputGroupAddon('s', addon_type="append", style={'width': '2em'})
                        ], className='mr-4'
                    )
                ], inline=True
            ),
            dbc.Row(
                [
                    dbc.Col(rows, width=4),
                    dbc.Col(id='result-col', width=8),
                ], className='mt-5'
            ),
        ],
        id='simulation-container'
    ),

    dbc.Container(
        [
            html.Iframe(
                src='/documentation/index.html',
            )
        ],
        className='embed-responsive',
        id='documentation-container',
    ),

    html.Footer(
        [
            html.A("FMPy %s" % fmpy.__version__, href='https://github.com/CATIA-Systems/FMPy', className='d-block text-muted small'),
        ], className='my-4 pt-3 border-top')

])


@app.callback(
    [Output('model-info-container', 'style'),
     Output('simulation-container', 'style'),
     Output('documentation-container', 'style')],
    [Input("tabs", "active_tab")])
def switch_tab(active_tab):
    return (
        {'display': 'block' if active_tab == 'model-info-tab' else 'none'},
        {'display': 'block' if active_tab == 'simulation-tab' else 'none'},
        {'display': 'block' if active_tab == 'documentation-tab' else 'none', 'height': '75vh'}
    )


@app.callback(
    Output('result-col', 'children'),
    [Input('simulate-button', 'n_clicks')],
    [State('stop-time', 'value')] + states
)
def update_output_div(n_clicks, stop_time, *values):

    try:
        start_values = dict(zip(names, values))

        result = simulate_fmu(filename=args.fmu_filename,
                              start_values=start_values,
                              stop_time=stop_time)

        fig = create_plotly_figure(result=result)

        return dcc.Graph(figure=fig)
    except Exception as e:
        return dbc.Alert("Simulation failed. %s" % e, color='danger'),


@app.server.route('/model.png')
def send_static_resource():
    return flask.send_from_directory(os.path.join(unzipdir), 'model.png', cache_timeout=0)


@app.server.route('/documentation/<resource>')
def serve_documentation(resource):
    return flask.send_from_directory(os.path.join(unzipdir, 'documentation'), resource, cache_timeout=0)


if __name__ == '__main__':
    app.run_server(host=args.host, port=args.port, debug=args.debug)
