/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 7:31 AM
 */

GCODE.gCodeReader = (function () {
    // ***** PRIVATE ******
    var gcode, lines;
    var z_heights = {};
    var model = [];
    var max = {x: undefined, y: undefined, z: undefined};
    var min = {x: undefined, y: undefined, z: undefined};
    var modelSize = {x: undefined, y: undefined, z: undefined};
    var boundingBox = {
        minX: undefined,
        maxX: undefined,
        minY: undefined,
        maxY: undefined,
        minZ: undefined,
        maxZ: undefined
    };
    var filamentByLayer = {};
    var printTimeByLayer;
    var totalFilament = 0;
    var printTime = 0;
    var speeds = {};
    var speedsByLayer = {};
    var gCodeOptions = {
        sortLayers: false,
        purgeEmptyLayers: true,
        analyzeModel: false,
        toolOffsets: [{x: 0, y: 0}],
        bed: {
            x: undefined,
            y: undefined,
            r: undefined,
            circular: undefined,
            centeredOrigin: undefined
        },
        ignoreOutsideBed: false,
        g90InfluencesExtruder: false,
        bedZ: 0
    };

    var rendererModel = undefined;
    var layerPercentageLookup = [];
    var cacheLookAhead = 64;
    var cacheLastLayer = undefined;
    var cacheLastCmd = undefined;

    var prepareGCode = function (totalSize) {
        if (!lines) return;
        gcode = [];
        var i, byteCount;

        byteCount = 0;
        for (i = 0; i < lines.length; i++) {
            byteCount += lines[i].length + 1; // line length + line ending
            gcode.push({line: lines[i], percentage: (byteCount * 100) / totalSize});
        }
        lines = [];
    };

    var searchInPercentageTree = function (key) {
        function searchInLayers(lower, upper, key) {
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    layerPercentageLookup[middle][0] <= key &&
                    layerPercentageLookup[middle][1] > key
                )
                    return middle;

                if (layerPercentageLookup[middle][0] > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        function searchInCmds(layer, lower, upper, key) {
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    rendererModel[layer][middle].percentage == key ||
                    (rendererModel[layer][middle].percentage <= key &&
                     rendererModel[layer][middle + 1].percentage > key)
                )
                    return middle;

                if (rendererModel[layer][middle].percentage > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        if (rendererModel === undefined) return undefined;

        // this happens when the print is stopped.
        // just return last position to keep the last
        // position on screen.
        if (key == null) return {layer: cacheLastLayer, cmd: cacheLastCmd};

        var bestLayer = undefined;
        var bestCmd = undefined;

        var bestLayer = searchInLayers(1, rendererModel.length - 1, key);
        var bestCmd = searchInCmds(
            bestLayer,
            0,
            rendererModel[bestLayer].length - 1,
            key
        );

        // remember last position
        cacheLastLayer = bestLayer;
        cacheLastCmd = bestCmd;

        return {layer: bestLayer, cmd: bestCmd};
    };

    var purgeLayers = function (m) {
        if (!m) return;
        var tmpModel = [];

        var purge;
        for (var i = 0; i < m.length; i++) {
            purge = true;

            if (typeof m[i] !== "undefined") {
                for (var j = 0; j < m[i].length; j++) {
                    if (m[i][j].extrude) {
                        purge = false;
                        break;
                    }
                }
            }

            if (!purge) {
                tmpModel.push(m[i]);
            }
        }

        return tmpModel;
    };

    var rebuildLayerPercentageLookup = function (m) {
        if (!m) return;

        var result = [];
        for (var i = 0; i < m.length - 1; i++) {
            if (!m[i]) {
                result[i] = [-1, -1];
                continue;
            }
            var start = m[i].length ? m[i][0].percentage : -1;

            var end = -1;
            for (var j = i + 1; j < m.length; j++) {
                if (m[j].length) {
                    end = m[j][0].percentage;
                    break;
                }
            }

            result[i] = [start, end];
        }
        result[m.length - 1] = [m[m.length - 1][0].percentage, 100];

        layerPercentageLookup = result;
    };
    
    // ***** PUBLIC *******
    return {
        clear: function () {
            model = [];
            z_heights = [];
            max = {x: undefined, y: undefined, z: undefined};
            min = {x: undefined, y: undefined, z: undefined};
            modelSize = {x: undefined, y: undefined, z: undefined};
            boundingBox = {
                minX: undefined,
                maxX: undefined,
                minY: undefined,
                maxY: undefined,
                minZ: undefined,
                maxZ: undefined
            };
            rendererModel = undefined;
            layerPercentageLookup = undefined;
            cacheLastLayer = undefined;
            cacheLastCmd = undefined;            
        },

        loadFile: function (reader) {
            this.clear();

            var totalSize = reader.target.result.length;
            // With a regex split below as previous, memory usage is huge & takes longer.
            lines = reader.target.result.replace("\r\n", "\n").split("\n");
            reader.target.result = null;
            prepareGCode(totalSize);

            GCODE.ui.worker.postMessage({
                cmd: "parseGCode",
                msg: {
                    gcode: gcode,
                    options: {
                        firstReport: 5,
                        toolOffsets: gCodeOptions["toolOffsets"],
                        bed: gCodeOptions["bed"],
                        ignoreOutsideBed: gCodeOptions["ignoreOutsideBed"],
                        g90InfluencesExtruder: gCodeOptions["g90InfluencesExtruder"],
                        bedZ: gCodeOptions["bedZ"]
                    }
                }
            });
        },

        setOption: function (options) {
            var dirty = false;
            _.forOwn(options, function (value, key) {
                if (value === undefined) return;
                dirty = dirty || gCodeOptions[key] !== value;
                gCodeOptions[key] = value;
            });
            if (dirty) {
                if (model && model.length > 0) this.passDataToRenderer();
            }
        },

        passDataToRenderer: function () {
            var m = model;
            if (gCodeOptions["purgeEmptyLayers"]) m = purgeLayers(m);

            rendererModel = m;
            rebuildLayerPercentageLookup(m);

            GCODE.renderer.doRender(m, 0);
            return m;
        },

        processLayerFromWorker: function (msg) {
            model[msg.layerNum] = msg.cmds;
            z_heights[msg.zHeightObject.zValue] = msg.zHeightObject.layer;
        },

        processMultiLayerFromWorker: function (msg) {
            for (var i = 0; i < msg.layerNum.length; i++) {
                model[msg.layerNum[i]] = msg.model[msg.layerNum[i]];
                z_heights[msg.zHeightObject.zValue[i]] = msg.layerNum[i];
            }
        },

        processAnalyzeModelDone: function (msg) {
            min = msg.min;
            max = msg.max;
            modelSize = msg.modelSize;
            boundingBox = msg.boundingBox;
            totalFilament = msg.totalFilament;
            filamentByLayer = msg.filamentByLayer;
            speeds = msg.speeds;
            speedsByLayer = msg.speedsByLayer;
            printTime = msg.printTime;
            printTimeByLayer = msg.printTimeByLayer;
        },

        getLayerFilament: function (z) {
            return filamentByLayer[z];
        },

        getLayerSpeeds: function (z) {
            return speedsByLayer[z] ? speedsByLayer[z] : {};
        },

        getModelInfo: function () {
            return {
                min: min,
                max: max,
                modelSize: modelSize,
                boundingBox: boundingBox,
                totalFilament: totalFilament,
                speeds: speeds,
                speedsByLayer: speedsByLayer,
                printTime: printTime,
                printTimeByLayer: printTimeByLayer
            };
        },

        getGCodeLines: function (layer, fromSegments, toSegments) {
            var result = {
                first: model[layer][fromSegments].gcodeLine,
                last: model[layer][toSegments].gcodeLine
            };
            return result;
        },

        getCmdIndexForPercentage: function (percentage) {
            return searchInPercentageTree(percentage);
        }
    };
})();
