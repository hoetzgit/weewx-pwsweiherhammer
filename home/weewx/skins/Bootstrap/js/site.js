let weewxData;
let weewxDataUrl = "weewxData.json";
let gauges = {};
let charts = {};
let lastAsyncReloadTimestamp = Date.now();
let lastGoodStamp = lastAsyncReloadTimestamp / 1000;
let archiveIntervalSeconds;
let localeWithDash;
let lang;
let eChartsLocale;
let maxAgeHoursMS;
let intervalData = {};

fetch(weewxDataUrl).then(function (u) {
    return u.json();
}).then(function (serverData) {
    weewxData = serverData;
    archiveIntervalSeconds = weewxData.config.archive_interval;
    localeWithDash = locale.replace("_", "-");
    lang = locale.split("_")[0];
    eChartsLocale = lang.toUpperCase();
    maxAgeHoursMS = weewxData.config.timespan * 3600000;

    let clients = [];
    if (weewxData !== undefined && weewxData.config !== undefined && weewxData.config.MQTT !== undefined && weewxData.config.MQTT.connections !== undefined) {
        for (let connectionId of Object.keys(weewxData.config.MQTT.connections)) {
            let connection = weewxData.config.MQTT.connections[connectionId];
            let mqttConnection = connection.broker_connection;
            let mqttUsername = connection.mqtt_username;
            let mqttPassword = connection.mqtt_password;
            let intervalData = {};

            let mqttCredentials;
            if (mqttUsername !== undefined) {
                mqttCredentials = {
                    username: mqttUsername
                };
                if (mqttPassword !== undefined) {
                    mqttCredentials["password"] = mqttPassword;
                }
            }
            if (mqttCredentials === undefined) {
                client = mqtt.connect(mqttConnection);
            } else {
                client = mqtt.connect(mqttConnection, mqttCredentials);
            }
            client.topics = connection.topics;
            clients.push(client);

            for (let topic of Object.keys(connection.topics)) {
                client.subscribe(topic);
            }

            client.on("message", function (topic, payload) {
                console.log(topic);
                checkAsyncReload();
                let jPayload = {};
                let topicConfig = this.topics[topic];
                if (topicConfig.type.toUpperCase() === "JSON") {
                    jPayload = JSON.parse(payload);
                } else if (topicConfig.type.toLowerCase() === "plain" && topicConfig.payload_key !== undefined) {
                    jPayload[topicConfig.payload_key] = parseFloat(payload);
                } else {
                    return;
                }

                let timestamp;
                if (jPayload.dateTime !== undefined) {
                    timestamp = parseInt(jPayload.dateTime) * 1000;
                } else {
                    timestamp = Date.now();
                }
                let date = new Date(timestamp);
                for (let gaugeId of Object.keys(gauges)) {
                    let gauge = gauges[gaugeId];
                    let value = convert(gauge.weewxData, getValue(jPayload, gauge.weewxData.payload_key));
                    if (!isNaN(value)) {
                        setGaugeValue(gauge, value, timestamp);
                    }
                }
                for (let chartId of Object.keys(charts)) {
                    let chart = charts[chartId];
                    chart.chartId = chartId;
                    if (chart.weewxData.aggregate_interval_minutes !== undefined) {
                        addAggregatedChartValues(chart, jPayload, timestamp, chart.weewxData.aggregate_interval_minutes);
                    } else {
                        addValues(chart, jPayload, timestamp);
                    }
                }
                let lastUpdate = document.getElementById("lastUpdate");
                lastUpdate.innerHTML = date.toLocaleDateString(localeWithDash) + ", " + date.toLocaleTimeString(localeWithDash);
            });
        }
    }
    if (typeof loadGauges === "function") {
        loadGauges();
    }
    if (typeof loadCharts === "function") {
        loadCharts();
    }
}).catch(err => {
    throw err
});

setInterval(checkAsyncReload, 60000);

function setGaugeValue(gauge, value, timestamp) {
    let option = gauge.getOption();
    let valueSeries = option.series[0];
    addValue(gauge.weewxData.dataset, value, timestamp);
    if (option.series[1] !== undefined) {
        option.series[1].axisLine.lineStyle.color = getHeatColor(valueSeries.max, valueSeries.min, valueSeries.splitNumber, valueSeries.axisTick.splitNumber, gauge.weewxData.dataset.data);
    }
    gauge.setOption(option);
    updateGaugeValue(value, gauge);
}

function updateGaugeValue(newValue, gauge) {
    let option = gauge.getOption();
    let currentValue = option.series[0].data[0].value;
    if (gauge.isCircular !== undefined && gauge.isCircular && Math.abs(newValue - currentValue) > 180) {
        let currentAnimationEasingUpdate = option.series[0].animationEasingUpdate;
        let currentAnimationSetting = option.animation;
        option.series[0].animationEasingUpdate = 'linear';
        let toNorth = 360;
        let fromNorth = 0;
        if (currentValue < 180) {
            toNorth = 0;
            fromNorth = 360;
        }
        option.series[0].data[0].value = toNorth;
        gauge.setOption(option);
        option.animation = false;
        option.series[0].data[0].value = fromNorth;
        gauge.setOption(option);
        option.animation = currentAnimationSetting;
        option.series[0].animationEasingUpdate = currentAnimationEasingUpdate;
        option.series[0].data[0].value = newValue;
        gauge.setOption(option);
    } else {
        option.series[0].data[0].value = newValue;
    }
    gauge.setOption(option);
}

function addAggregatedChartValues(chart, jPayload, timestamp, aggregateIntervalMinutes) {
    let option = chart.getOption();
    for (let dataset of option.series) {
        let value = convert(chart.weewxData[dataset.weewxColumn], getValue(jPayload, dataset.payloadKey));
        if (!isNaN(value)) {
            addAggregatedChartValue(dataset, value, timestamp, aggregateIntervalMinutes);
            chart.setOption(option);
            if (chart.chartId !== undefined) {
                let chartElem = document.getElementById(chart.chartId + "_timestamp");
                chartElem.innerHTML = formatDateTime(timestamp);
            }
        }
    }
}

function addValues(chart, jPayload, timestamp) {
    let option = chart.getOption();
    for (let dataset of option.series) {
        dataset.chartId = chart.chartId;
        let value = convert(chart.weewxData[dataset.weewxColumn], getValue(jPayload, dataset.payloadKey));
        if (!isNaN(value)) {
            addValue(dataset, value, timestamp);
            chart.setOption(option);
        }
    }
}

function addValue(dataset, value, timestamp) {
    let type = dataset.weewxColumn;
    let intervalStart = getIntervalStart(timestamp, archiveIntervalSeconds * 1000);
    let data = dataset.data;

    let currentIntervalData = getIntervalData(type, intervalStart);
    if (type === "windSpeed") {
        //some stations update windSpeed more often than gust: if current speed > gust, update gust, but only for current gauge value
        //other values will be updated when regular message arrives
        let windGustGauge = gauges.windGustGauge;
        if (windGustGauge !== undefined && value > windGustGauge.getOption().series[0].data[0].value) {
            setGaugeValue(windGustGauge, value, timestamp);
        }
    }
    currentIntervalData.values.push(value);
    if (data.length > 0 && data[data.length - 1][0] > intervalStart) {
        data.pop();
        value = getIntervalValue(type, currentIntervalData, value);
    }
    data.push([timestamp, value]);
    if (dataset.chartId !== undefined) {
        let chartElem = document.getElementById(dataset.chartId + "_timestamp");
        chartElem.innerHTML = formatDateTime(timestamp);
    }
    rotateData(dataset.data);
}

function getIntervalData(type, intervalStart) {
    if (intervalData[type] === undefined || intervalData[type].startTime !== intervalStart) {
        let currentIntervalData = {
            startTime: intervalStart,
            values: []
        };
        intervalData[type] = currentIntervalData;
        return currentIntervalData;
    } else {
        return currentIntervalData = intervalData[type];
    }
}

function getIntervalValue(type, currentIntervalData, value) {
    if (type === "windGust") {
        return getMaxIntervalValue(currentIntervalData, value);
    }
    if (type === "windDir") {
        return calcWindDir(currentIntervalData, intervalData.windSpeed);
    }
    return getAverageIntervalValue(currentIntervalData, value);
}

function getMaxIntervalValue(currentIntervalData, value) {
    let max = value;
    for (let aValue of currentIntervalData.values) {
        if (aValue > max) {
            max = aValue;
        }
    }
    return max;
}

function getAverageIntervalValue(currentIntervalData, value) {
    let sum = value;
    for (let aValue of currentIntervalData.values) {
        value += aValue;
    }
    return value / (currentIntervalData.values.length + 1);
}

function addAggregatedChartValue(dataset, value, timestamp, intervalMinutes) {
    setAggregatedChartEntry(value, timestamp, intervalMinutes, dataset.data);
    rotateData(dataset.data);
}

function setAggregatedChartEntry(value, timestamp, intervalMinutes, data) {
    let duration = intervalMinutes * 60000;
    let intervalStart = getIntervalStart(timestamp, duration) + duration / 2;
    if (data.length > 0 && data[data.length - 1][0] === intervalStart) {
        let intervalSum = Number.parseFloat(data[data.length - 1][1]) + value;
        data[data.length - 1][1] = intervalSum;
    } else {
        data.push([intervalStart, value]);
    }
}

function rotateData(data) {
    if (data === undefined || data[0] === undefined || data[0][0] === undefined) {
        return;
    }
    while (data.length > 0 && data[0][0] < Date.now() - maxAgeHoursMS) {
        data.shift();
    }
}

function calculateDewpoint(temp, humidity) {
    humidity = Number.parseFloat(humidity) / 100;
    temp = Number.parseFloat(temp);
    if (temp > 0) {
        return 243.12 * ((17.62 * temp) / (243.12 + temp) + Math.log(humidity)) / ((17.62 * 243.12) / (243.12 + temp) - Math.log(humidity));
    }
    return 272.62 * ((22.46 * temp) / (272.62 + temp) + Math.log(humidity)) / ((22.46 * 272.62) / (272.62 + temp) - Math.log(humidity));
}

function getIntervalStart(timestamp, duration) {
    return Math.floor((+timestamp) / (+duration)) * (+duration)
}

function calcWindDir(windDirIntervaldata, windSpeedIntervaldata) {
    let sumX = 0;
    let sumY = 0;
    for (let i = 0; i < windSpeedIntervaldata.values.length; i++) {
        let windSpeed = windSpeedIntervaldata.values[i];
        if (windSpeed > 0) {
            let windDir = (windDirIntervaldata.values[i]) * Math.PI / 180;
            sumX += Math.cos(windDir) * windSpeed;
            sumY += Math.sin(windDir) * windSpeed;
        }
    }
    let offset = 0;
    if (sumX.toFixed(3) === "0.000" && sumY.toFixed(3) === "0.000") { //no windDir, toFixed because of Number precision
        return NaN;
    } else if (sumX >= 0) {
        if (sumY < 0) {
            offset = 360;
        }
    } else {
        offset = 180;
    }
    return (Math.atan(sumY / sumX) * 180 / Math.PI) + offset;
}

function formatDateTime(timestamp) {
    let date = new Date(timestamp);
    return date.toLocaleDateString(localeWithDash) + ", " + date.toLocaleTimeString(localeWithDash);
}

function checkAsyncReload() {
    if ((Date.now() - lastAsyncReloadTimestamp) / 1000 > archiveIntervalSeconds) {
        fetch("ts.json").then(function (u) {
            return u.json();
        }).then(function (serverData) {
            if (Number.parseInt(serverData.lastGoodStamp) > lastGoodStamp) {
                lastGoodStamp = serverData.lastGoodStamp;
                asyncReloadWeewxData();
            }
        }).catch(err => {
            throw err
        });
    }
}

function asyncReloadWeewxData() {
    fetch(weewxDataUrl).then(function (u) {
        return u.json();
    }).then(function (serverData) {
        weewxData = serverData;
        loadGauges();
        if (typeof loadCharts === 'function') {
            loadCharts();
        }
        let date = new Date(lastGoodStamp * 1000);
        let lastUpdate = document.getElementById("lastUpdate");
        lastUpdate.innerHTML = date.toLocaleDateString(localeWithDash) + ", " + date.toLocaleTimeString(localeWithDash);
    }).catch(err => {
        throw err
    });
}

function getValue(obj, path) {
    if (path === undefined) {
        return;
    }
    let pathArray = path.split(".");
    let value = obj;
    for (let i = 0; i < pathArray.length; i++) {
        if (value !== undefined && value[pathArray[i]] !== undefined) {
            value = value[pathArray[i]];
        }
    }
    return value;
}