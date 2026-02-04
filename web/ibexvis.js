console.log("Initialising")

import "https://cdn.plot.ly/plotly-3.2.0.min.js";
import "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js";

console.log("Loaded pyodide and plotly")

let pyodide = await loadPyodide();
await pyodide.loadPackage(["numpy", "matplotlib", "micropip"]);
const micropip = pyodide.pyimport("micropip");
await micropip.install("ibex_vis-0.0.1-py3-none-any.whl");

console.log("Loaded IbexVis");

const plotdiv = document.getElementById("Plot");
const p0 = {x:[0], y:[0]}, lgl = {x:1, y:1, xanchor:'right'};
const plotlayout = {xaxis: {title: 'Time (s)'}, yaxis: {title: 'Plot Variable'}, legend:lgl};
Plotly.newPlot(plotdiv, [p0], plotlayout, {responsive: true});
document.getElementById("intro").remove();


const formdata = (time, propname, datavec) => [...propname].map((_, c) => {
  return {x:time, y:datavec[c], xaxis:'x'+(c+1), yaxis:'y'+(c+1), type:'scatter', name:propname[c]};
});

const genshapes = (runs, colour) => runs.map((d) => {
  return {
    type: 'rect',
    // x-reference is assigned to the x-values
    xref: 'x',
    // y-reference is assigned to the plot paper [0,1]
    yref: 'paper',
    x0: d[0],
    x1: d[1],
    y0: 0,
    y1: 1,
    fillcolor: colour,
    opacity: 0.2,
    line: {width: 0}
  };
});

// Script upload
document.getElementById("upload-button").onclick = function () {
  const filedata = document.getElementById("upload").files;
  if (filedata.length !== 1) return;

  console.log("File selected: ", filedata[0].name);
  const reader = new FileReader();
  reader.readAsText(filedata[0]);

  reader.addEventListener("load", () => {
    document.getElementById("scriptpy").value = reader.result;
  });
};

document.getElementById("calcbutton").onclick = function calcVis() {
  const scriptpy = document.getElementById("scriptpy").value;
  pyodide.FS.writeFile("script.py", scriptpy);
  const configjson = document.getElementById("configjson").value;
  pyodide.FS.writeFile("config.json", configjson);
  let rundata = false;
  plotdiv.textContent = "";
  try {
    rundata = pyodide.runPython(`
      from ibex_vis.vis import runner, properties_from_input, Path
      run = runner("script.py", properties_from_input(Path("config.json")),
                   dummies={"genie_python": "ibex_vis.dummy_genie", "inst": "ibex_vis.dummy_inst"})
      props = run.properties.keys() - {"time"}
      time = run.properties["time"].data
      (time, props, [run.properties[name].data for name in props], run.counts, run.records)
    `).toJs();
  } catch(err) {
    plotdiv.innerHTML = "<pre>" + err + "</pre>";
  }

  var records = genshapes(rundata[3], '#00d300').concat(genshapes(rundata[4], '#d30000'));

  if (rundata) {
    const layout = { grid: {rows: rundata[2].length, columns:1, pattern:'independent'}, shapes: records };
    const data = formdata(rundata[0], Array.from(rundata[1]), rundata[2]);
    Plotly.newPlot(plotdiv, data, layout);
  }
}
