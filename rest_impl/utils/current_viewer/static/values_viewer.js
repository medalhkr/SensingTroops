google.load("visualization", "1", {packages:["corechart"]});
google.setOnLoadCallback(draw);

// get params
var purpose = $("#param_purpose").text();
var place = $("#param_place").text();
var type = $("#param_type").text();

function draw() {
  if (place != "All") {
    var chart_dom = $("<span></span>");
    draw_graph(chart_dom[0], purpose, place, type);
    $("#graphs").append(chart_dom);
  } else {
    [
      "Floor-5",
      "Floor-4",
      "Floor-3",
      "Floor-2",
      "Floor-1"
    ].map(function (floor) {
      var w_dom = $("<span></span>");
      draw_graph(w_dom[0], purpose, floor + ".west-side", type);
      var e_dom = $("<span></span>");
      draw_graph(e_dom[0], purpose, floor + ".east-side", type);
      $("#graphs").append(w_dom);
      $("#graphs").append(e_dom);
      $("#graphs").append($("<br>"));
    });
  }
}

function draw_graph(dom, purpose, place, type) {

  var url = "./values/" + purpose + "/" + place + "/" + type;
  $.getJSON(url, function (res) {
    console.log(res);
    var data = new google.visualization.DataTable();
    data.addColumn('datetime', '日時');

    var unit = res.values[0][2];
    values = res.values.map(function (elem) {
      return [new Date(elem[0]), elem[1]];
    });
    if (values[0][1].length == undefined) {
      data.addColumn('number', '値');
    } else {
      data.addColumn('number', 'x');
      data.addColumn('number', 'y');
      data.addColumn('number', 'z');
      values = values.map(function (elem) {
        return [elem[0]].concat(elem[1]);
      });
    }
    data.addRows(values);

    var options = {
      title: place,
      hAxis: {title: '日時'},
      vAxis: {title: unit},
      width: 1000,
      height: 250,
      pointSize: 1
    };

    var chart = new google.visualization.LineChart(dom);
    chart.draw(data, options);
  });
}
