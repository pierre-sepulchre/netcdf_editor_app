FROM python:3.8

# Install system dependencies for HDF5 and netcdf
RUN apt-get update && apt-get install -y libhdf5-dev libnetcdf-dev libgeos-dev && rm -rf /var/lib/apt/lists/*

# Setup the enviroment
COPY requirements.*txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY flask_app /usr/src/app/flask_app
RUN pip install /usr/src/app/flask_app
COPY python_tools /usr/src/app/python_tools
RUN pip install /usr/src/app/python_tools
WORKDIR /usr/src/app/python_tools/climpy/interactive

ENV BOKEH_RESOURCES=cdn

COPY services/panel/holoviews.patch /usr/src/holoviews.patch
RUN patch /usr/local/lib/python3.8/site-packages/holoviews/plotting/util.py /usr/src/holoviews.patch

ENTRYPOINT [  "python", "-m", "panel",  "serve",  "--port=5006", "--address=0.0.0.0", "--websocket-max-message-size=100000000", "internal_oceans.py", "value_changer.py", "passage_problems.py", "sub_basins.py" ]