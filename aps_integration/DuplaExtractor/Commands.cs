using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Collections.Generic;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.EditorInput;

// This assembly attribute explicitly registers our CommandClass
[assembly: CommandClass(typeof(DuplaExtractor.Commands))]
[assembly: ExtensionApplication(null)]

namespace DuplaExtractor
{
    public class Commands
    {
        private const double MinArea = 1e-6;
        private const double GeometryEpsilon = 1e-9;
        private const double BulgeEpsilon = 1e-10;
        private const double PlanarityRelativeTolerance = 1e-8;
        private const string AreaModeConfigFileName = "dupla_area_mode.txt";

        private enum AreaComputationMode
        {
            Improved,
            Legacy,
        }

        private static readonly Lazy<AreaComputationMode> CachedAreaComputationMode =
            new Lazy<AreaComputationMode>(LoadAreaComputationMode);

        private sealed class BlockData
        {
            public string Handle { get; set; } = "";
            public string Layer { get; set; } = "";
            public string Name { get; set; } = "";
            public Dictionary<string, string> Attributes { get; set; } = new Dictionary<string, string>();
            public PointData Position { get; set; } = new PointData();
        }

        private sealed class PolylineData
        {
            public string Handle { get; set; } = "";
            public string Layer { get; set; } = "";
            public double Area { get; set; }
            public double Length { get; set; }
            public bool Closed { get; set; }
            public int VertexCount { get; set; }
        }

        private sealed class AreaData
        {
            public string Handle { get; set; } = "";
            public string Layer { get; set; } = "";
            public string EntityType { get; set; } = "";
            public double Area { get; set; }
            public double Perimeter { get; set; }
            public bool Closed { get; set; }
            public string MeasurementKind { get; set; } = "";
            public string Source { get; set; } = "";
            public bool FromBlockReference { get; set; }
            public string ParentBlock { get; set; } = "";
            public int NestingDepth { get; set; }
            public PointData Center { get; set; }
        }

        private sealed class PointData
        {
            public double X { get; set; }
            public double Y { get; set; }
            public double Z { get; set; }
        }

        private sealed class BlockContext
        {
            public string Name { get; set; } = "";
            public int Depth { get; set; }
        }

        private sealed class ProgressTracker
        {
            private const int TopLevelLogInterval = 250;
            private const int BlockEntityLogInterval = 1000;

            private readonly Editor _editor;
            private readonly DateTime _startedUtc = DateTime.UtcNow;
            private int _topLevelEntities;
            private int _blockEntities;

            public ProgressTracker(Editor editor)
            {
                _editor = editor;
            }

            public void RecordTopLevelEntity()
            {
                _topLevelEntities++;
                if (_topLevelEntities % TopLevelLogInterval == 0)
                {
                    ReportPhase($"ModelSpace procesado: {_topLevelEntities} entidades.");
                }
            }

            public void RecordBlockEntity(string blockPath, int depth)
            {
                _blockEntities++;
                if (_blockEntities % BlockEntityLogInterval == 0)
                {
                    ReportPhase($"Bloques explotados: {_blockEntities} entidades (depth={depth}, block={blockPath}).");
                }
            }

            public void ReportPhase(string message)
            {
                if (_editor == null)
                {
                    return;
                }

                try
                {
                    TimeSpan elapsed = DateTime.UtcNow - _startedUtc;
                    _editor.WriteMessage($"\n[DuplaExtractor +{elapsed:mm\\:ss}] {message}");
                }
                catch
                {
                    // Ignore logging failures; extraction must continue.
                }
            }
        }

        [CommandMethod("ExtractDuplaData")]
        public void ExtractDuplaData()
        {
            var db = HostApplicationServices.WorkingDatabase;
            var results = new Dictionary<string, object>();
            var blocks = new List<BlockData>();
            var polylines = new List<PolylineData>();
            var areas = new List<AreaData>();
            var progress = new ProgressTracker(TryGetEditor());
            string areaMode = GetAreaComputationModeName();
            progress.ReportPhase($"Iniciando analisis de areas (mode={areaMode}).");

            using (var tr = db.TransactionManager.StartTransaction())
            {
                var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                var btr = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                foreach (ObjectId objId in btr)
                {
                    var ent = tr.GetObject(objId, OpenMode.ForRead) as Entity;
                    if (ent == null)
                    {
                        continue;
                    }

                    progress.RecordTopLevelEntity();

                    if (ent is BlockReference br)
                    {
                        blocks.Add(ExtractBlockData(tr, br));
                        CollectBlockAreas(tr, br, areas, GetBlockName(tr, br), 1, progress);
                        continue;
                    }

                    if (ent is Polyline pline)
                    {
                        polylines.Add(ExtractPolylineData(pline));
                    }

                    AddAreaIfAny(tr, ent, areas, null);
                }

                results["Blocks"] = blocks;
                results["Polylines"] = polylines;
                results["Areas"] = areas;
                results["AreaComputationMode"] = areaMode;
                results["AreaSummary"] = BuildAreaSummary(areas);
                tr.Commit();
            }

            // Design Automation siempre devuelve los resultados en el directorio actual (working directory)
            var jsonOptions = new JsonSerializerOptions { WriteIndented = true };
            progress.ReportPhase($"Serializando resultados.json ({areas.Count} areas).");
            string jsonString = JsonSerializer.Serialize(results, jsonOptions);
            File.WriteAllText("resultados.json", jsonString);

            progress.ReportPhase("Serializando resultados_areas.json.");
            var areaStudyReport = BuildAreaStudyReport(db, blocks, polylines, areas, areaMode);
            string areasJsonString = JsonSerializer.Serialize(areaStudyReport, jsonOptions);
            File.WriteAllText("resultados_areas.json", areasJsonString);
            progress.ReportPhase("Extraccion finalizada.");
        }

        private static BlockData ExtractBlockData(Transaction tr, BlockReference br)
        {
            var props = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            foreach (ObjectId attId in br.AttributeCollection)
            {
                var att = tr.GetObject(attId, OpenMode.ForRead) as AttributeReference;
                if (att != null)
                {
                    props[att.Tag] = att.TextString ?? "";
                }
            }

            if (br.IsDynamicBlock)
            {
                foreach (DynamicBlockReferenceProperty prop in br.DynamicBlockReferencePropertyCollection)
                {
                    props[prop.PropertyName] = prop.Value?.ToString() ?? "";
                }
            }

            return new BlockData
            {
                Handle = SafeHandle(br),
                Layer = SafeLayer(br),
                Name = GetBlockName(tr, br),
                Attributes = props,
                Position = new PointData
                {
                    X = br.Position.X,
                    Y = br.Position.Y,
                    Z = br.Position.Z,
                },
            };
        }

        private static PolylineData ExtractPolylineData(Polyline pline)
        {
            double area = 0.0;

            if (pline.Closed)
            {
                try
                {
                    area = Math.Abs(pline.Area);
                }
                catch
                {
                    area = 0.0;
                }
            }

            return new PolylineData
            {
                Handle = SafeHandle(pline),
                Layer = SafeLayer(pline),
                Area = area,
                Length = SafeLength(pline.Length),
                Closed = pline.Closed,
                VertexCount = pline.NumberOfVertices,
            };
        }

        private static void CollectBlockAreas(
            Transaction tr,
            BlockReference br,
            List<AreaData> areas,
            string blockPath,
            int depth,
            ProgressTracker progress)
        {
            var exploded = new DBObjectCollection();

            try
            {
                br.Explode(exploded);
            }
            catch
            {
                return;
            }

            foreach (DBObject dbObj in exploded)
            {
                try
                {
                    if (!(dbObj is Entity entity))
                    {
                        continue;
                    }

                    progress?.RecordBlockEntity(blockPath, depth);

                    if (entity is BlockReference nestedBlock)
                    {
                        string nestedName = GetBlockName(tr, nestedBlock);
                        string nestedPath = string.IsNullOrWhiteSpace(blockPath)
                            ? nestedName
                            : $"{blockPath}/{nestedName}";

                        CollectBlockAreas(tr, nestedBlock, areas, nestedPath, depth + 1, progress);
                        continue;
                    }

                    AddAreaIfAny(
                        tr,
                        entity,
                        areas,
                        new BlockContext
                        {
                            Name = blockPath,
                            Depth = depth,
                        });
                }
                finally
                {
                    dbObj.Dispose();
                }
            }
        }

        private static void AddAreaIfAny(
            Transaction tr,
            Entity entity,
            List<AreaData> areas,
            BlockContext blockContext)
        {
            if (!TryBuildAreaData(tr, entity, blockContext, out AreaData areaData))
            {
                return;
            }

            areas.Add(areaData);
        }

        private static bool TryBuildAreaData(
            Transaction tr,
            Entity entity,
            BlockContext blockContext,
            out AreaData areaData)
        {
            areaData = null;

            double area;
            double perimeter = 0.0;
            bool closed = true;
            string source;
            string measurementKind;

            if (entity is Polyline pline)
            {
                if (!pline.Closed)
                {
                    return false;
                }

                try
                {
                    area = Math.Abs(pline.Area);
                }
                catch
                {
                    return false;
                }

                perimeter = SafeLength(pline.Length);
                source = "polyline-area-property";
                measurementKind = "closed_boundary";
            }
            else if (entity is Polyline2d polyline2d)
            {
                if (!polyline2d.Closed)
                {
                    return false;
                }

                if (!TryComputePolyline2dMetrics(tr, polyline2d, out area, out perimeter, out source))
                {
                    return false;
                }

                measurementKind = "closed_boundary";
            }
            else if (entity is Polyline3d polyline3d)
            {
                if (!polyline3d.Closed)
                {
                    return false;
                }

                if (!TryComputePolyline3dMetrics(tr, polyline3d, out area, out perimeter, out source))
                {
                    return false;
                }

                measurementKind = "closed_boundary";
            }
            else if (entity is Circle circle)
            {
                area = Math.PI * circle.Radius * circle.Radius;
                perimeter = 2.0 * Math.PI * circle.Radius;
                source = "circle-analytic";
                measurementKind = "analytic_curve";
            }
            else if (TryGetAreaViaProperty(entity, out area))
            {
                source = GetNativeAreaSource(entity);
                measurementKind = GetMeasurementKind(entity);
                TryGetLengthViaProperty(entity, out perimeter);
            }
            else if (LooksLikeEllipse(entity) && TryGetEllipseArea(entity, out area, out perimeter))
            {
                source = "ellipse-analytic";
                measurementKind = "analytic_curve";
            }
            else
            {
                return false;
            }

            area = Math.Abs(area);
            perimeter = Math.Abs(perimeter);

            if (!IsFinitePositive(area))
            {
                return false;
            }

            areaData = new AreaData
            {
                Handle = SafeHandle(entity),
                Layer = SafeLayer(entity),
                EntityType = entity.GetType().Name,
                Area = area,
                Perimeter = perimeter,
                Closed = closed,
                MeasurementKind = measurementKind,
                Source = source,
                FromBlockReference = blockContext != null,
                ParentBlock = blockContext?.Name ?? "",
                NestingDepth = blockContext?.Depth ?? 0,
                Center = TryGetCenter(entity),
            };

            return true;
        }

        private static object BuildAreaSummary(List<AreaData> areas)
        {
            return new
            {
                Count = areas.Count,
                TotalArea = areas.Sum(a => a.Area),
                ByMeasurementKind = areas
                    .GroupBy(a => a.MeasurementKind)
                    .Select(g => new
                    {
                        MeasurementKind = g.Key,
                        Count = g.Count(),
                        TotalArea = g.Sum(x => x.Area),
                    })
                    .OrderByDescending(x => x.TotalArea)
                    .ToList(),
                ByLayer = areas
                    .GroupBy(a => a.Layer)
                    .Select(g => new
                    {
                        Layer = g.Key,
                        Count = g.Count(),
                        TotalArea = g.Sum(x => x.Area),
                    })
                    .OrderByDescending(x => x.TotalArea)
                    .ToList(),
            };
        }

        private static object BuildAreaStudyReport(
            Database db,
            List<BlockData> blocks,
            List<PolylineData> polylines,
            List<AreaData> areas,
            string areaMode)
        {
            var orderedAreas = areas
                .OrderByDescending(a => a.Area)
                .ThenBy(a => a.Layer)
                .ToList();

            return new
            {
                SourceDrawing = GetSourceDrawingName(db),
                GeneratedAtUtc = DateTime.UtcNow.ToString("o"),
                AreaComputationMode = areaMode,
                Counts = new
                {
                    Blocks = blocks.Count,
                    Polylines = polylines.Count,
                    ClosedPolylines = polylines.Count(p => p.Closed),
                    Areas = orderedAreas.Count,
                    AreasFromBlockReferences = orderedAreas.Count(a => a.FromBlockReference),
                    TopLevelAreas = orderedAreas.Count(a => !a.FromBlockReference),
                },
                Summary = new
                {
                    TotalArea = orderedAreas.Sum(a => a.Area),
                    ByMeasurementKind = orderedAreas
                        .GroupBy(a => a.MeasurementKind)
                        .Select(g => new
                        {
                            MeasurementKind = g.Key,
                            Count = g.Count(),
                            TotalArea = g.Sum(x => x.Area),
                        })
                        .OrderByDescending(x => x.TotalArea)
                        .ToList(),
                    ByLayer = orderedAreas
                        .GroupBy(a => a.Layer)
                        .Select(g => new
                        {
                            Layer = g.Key,
                            Count = g.Count(),
                            TotalArea = g.Sum(x => x.Area),
                        })
                        .OrderByDescending(x => x.TotalArea)
                        .ToList(),
                    ByEntityType = orderedAreas
                        .GroupBy(a => a.EntityType)
                        .Select(g => new
                        {
                            EntityType = g.Key,
                            Count = g.Count(),
                            TotalArea = g.Sum(x => x.Area),
                        })
                        .OrderByDescending(x => x.TotalArea)
                        .ToList(),
                    BySource = orderedAreas
                        .GroupBy(a => a.Source)
                        .Select(g => new
                        {
                            Source = g.Key,
                            Count = g.Count(),
                            TotalArea = g.Sum(x => x.Area),
                        })
                        .OrderByDescending(x => x.TotalArea)
                        .ToList(),
                    ByParentBlock = orderedAreas
                        .Where(a => !string.IsNullOrWhiteSpace(a.ParentBlock))
                        .GroupBy(a => a.ParentBlock)
                        .Select(g => new
                        {
                            ParentBlock = g.Key,
                            Count = g.Count(),
                            TotalArea = g.Sum(x => x.Area),
                        })
                        .OrderByDescending(x => x.TotalArea)
                        .Take(200)
                        .ToList(),
                },
                TopAreas = orderedAreas.Take(250).ToList(),
            };
        }

        private static bool TryComputePolyline2dMetrics(
            Transaction tr,
            Polyline2d polyline2d,
            out double area,
            out double perimeter,
            out string source)
        {
            if (GetAreaComputationMode() == AreaComputationMode.Legacy)
            {
                return TryComputePolyline2dLegacyMetrics(tr, polyline2d, out area, out perimeter, out source);
            }

            area = 0.0;
            perimeter = 0.0;
            source = "";

            if (TryGetNativeCurveMetrics(polyline2d, out area, out perimeter))
            {
                source = "polyline2d-native-curve-area";
                return true;
            }

            if (!TryGetPolyline2dVertices(tr, polyline2d, out List<(Point3d Position, double Bulge)> vertices))
            {
                return false;
            }

            if (!TryProjectPolyline2dVertices(vertices, polyline2d.Normal, out List<(double X, double Y, double Bulge)> planarVertices))
            {
                return false;
            }

            if (!TryComputePlanarPolylineAreaAndPerimeter(planarVertices, out area, out perimeter))
            {
                return false;
            }

            source = HasBulgedSegments(planarVertices)
                ? "polyline2d-planar-bulge-fallback"
                : "polyline2d-planar-shoelace-fallback";

            return true;
        }

        private static bool TryComputePolyline2dLegacyMetrics(
            Transaction tr,
            Polyline2d polyline2d,
            out double area,
            out double perimeter,
            out string source)
        {
            area = 0.0;
            perimeter = 0.0;
            source = "";

            if (!TryGetLegacyPolyline2dVertices(tr, polyline2d, out List<(double X, double Y)> points))
            {
                return false;
            }

            area = ComputePolygonArea(points);
            perimeter = ComputePolylineLength(points, true);
            source = "polyline2d-legacy-shoelace-xy";
            return IsFinitePositive(area) && IsFinite(perimeter);
        }

        private static bool TryComputePolyline3dMetrics(
            Transaction tr,
            Polyline3d polyline3d,
            out double area,
            out double perimeter,
            out string source)
        {
            if (GetAreaComputationMode() == AreaComputationMode.Legacy)
            {
                return TryComputePolyline3dLegacyMetrics(tr, polyline3d, out area, out perimeter, out source);
            }

            area = 0.0;
            perimeter = 0.0;
            source = "";

            if (TryGetNativeCurveMetrics(polyline3d, out area, out perimeter))
            {
                source = "polyline3d-native-curve-area";
                return true;
            }

            if (!TryGetPolyline3dVertices(tr, polyline3d, out List<Point3d> points))
            {
                return false;
            }

            perimeter = ComputePolylineLength3d(points, true);
            if (!TryComputePlanarPolygonArea3d(points, out area))
            {
                return false;
            }

            source = "polyline3d-planar-newell-fallback";
            return true;
        }

        private static bool TryComputePolyline3dLegacyMetrics(
            Transaction tr,
            Polyline3d polyline3d,
            out double area,
            out double perimeter,
            out string source)
        {
            area = 0.0;
            perimeter = 0.0;
            source = "";

            if (!TryGetLegacyPolyline3dVertices(tr, polyline3d, out List<(double X, double Y)> points))
            {
                return false;
            }

            area = ComputePolygonArea(points);
            perimeter = ComputePolylineLength(points, true);
            source = "polyline3d-legacy-shoelace-xy";
            return IsFinitePositive(area) && IsFinite(perimeter);
        }

        private static bool TryGetPolyline2dVertices(
            Transaction tr,
            Polyline2d polyline2d,
            out List<(Point3d Position, double Bulge)> vertices)
        {
            vertices = new List<(Point3d Position, double Bulge)>();

            foreach (ObjectId vertexId in polyline2d)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as Vertex2d;
                if (vertex == null)
                {
                    continue;
                }

                if (!IsAreaVertex(vertex))
                {
                    return false;
                }

                vertices.Add((vertex.Position, vertex.Bulge));
            }

            return vertices.Count >= 3;
        }

        private static bool TryGetLegacyPolyline2dVertices(
            Transaction tr,
            Polyline2d polyline2d,
            out List<(double X, double Y)> points)
        {
            points = new List<(double X, double Y)>();

            foreach (ObjectId vertexId in polyline2d)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as Vertex2d;
                if (vertex == null)
                {
                    continue;
                }

                points.Add((vertex.Position.X, vertex.Position.Y));
            }

            return points.Count >= 3;
        }

        private static bool TryGetPolyline3dVertices(
            Transaction tr,
            Polyline3d polyline3d,
            out List<Point3d> points)
        {
            points = new List<Point3d>();

            foreach (ObjectId vertexId in polyline3d)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as PolylineVertex3d;
                if (vertex == null)
                {
                    continue;
                }

                if (!IsAreaVertex(vertex))
                {
                    return false;
                }

                points.Add(vertex.Position);
            }

            return points.Count >= 3;
        }

        private static bool TryGetLegacyPolyline3dVertices(
            Transaction tr,
            Polyline3d polyline3d,
            out List<(double X, double Y)> points)
        {
            points = new List<(double X, double Y)>();

            foreach (ObjectId vertexId in polyline3d)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as PolylineVertex3d;
                if (vertex == null)
                {
                    continue;
                }

                points.Add((vertex.Position.X, vertex.Position.Y));
            }

            return points.Count >= 3;
        }

        private static bool TryProjectPolyline2dVertices(
            List<(Point3d Position, double Bulge)> vertices,
            Vector3d normal,
            out List<(double X, double Y, double Bulge)> planarVertices)
        {
            planarVertices = new List<(double X, double Y, double Bulge)>();

            if (vertices.Count < 3 || !TryBuildPlaneBasis(normal, out Vector3d axisX, out Vector3d axisY))
            {
                return false;
            }

            Point3d origin = vertices[0].Position;

            foreach (var vertex in vertices)
            {
                Vector3d offset = vertex.Position - origin;
                planarVertices.Add((
                    offset.DotProduct(axisX),
                    offset.DotProduct(axisY),
                    vertex.Bulge));
            }

            return true;
        }

        private static bool TryBuildPlaneBasis(Vector3d normal, out Vector3d axisX, out Vector3d axisY)
        {
            axisX = new Vector3d();
            axisY = new Vector3d();

            if (!IsFinite(normal.Length) || normal.Length <= GeometryEpsilon)
            {
                return false;
            }

            Vector3d unitNormal = normal.GetNormal();
            Vector3d basisHint = Math.Abs(unitNormal.DotProduct(Vector3d.ZAxis)) > 0.9
                ? Vector3d.XAxis
                : Vector3d.ZAxis;

            axisX = basisHint.CrossProduct(unitNormal);
            if (axisX.Length <= GeometryEpsilon)
            {
                axisX = Vector3d.YAxis.CrossProduct(unitNormal);
                if (axisX.Length <= GeometryEpsilon)
                {
                    return false;
                }
            }

            axisX = axisX.GetNormal();
            axisY = unitNormal.CrossProduct(axisX).GetNormal();
            return true;
        }

        private static bool TryComputePlanarPolylineAreaAndPerimeter(
            List<(double X, double Y, double Bulge)> vertices,
            out double area,
            out double perimeter)
        {
            area = 0.0;
            perimeter = 0.0;

            if (vertices.Count < 3)
            {
                return false;
            }

            double signedArea = ComputeSignedPolygonArea(vertices.Select(v => (v.X, v.Y)).ToList());

            for (int i = 0; i < vertices.Count; i++)
            {
                int j = (i + 1) % vertices.Count;
                double dx = vertices[j].X - vertices[i].X;
                double dy = vertices[j].Y - vertices[i].Y;
                double chordLength = Math.Sqrt((dx * dx) + (dy * dy));

                if (!IsFinite(chordLength))
                {
                    return false;
                }

                double bulge = vertices[i].Bulge;
                if (Math.Abs(bulge) <= BulgeEpsilon || chordLength <= GeometryEpsilon)
                {
                    perimeter += chordLength;
                    continue;
                }

                double centralAngle = 4.0 * Math.Atan(Math.Abs(bulge));
                double halfAngleSin = Math.Sin(centralAngle / 2.0);
                if (Math.Abs(halfAngleSin) <= GeometryEpsilon)
                {
                    return false;
                }

                double radius = chordLength / (2.0 * halfAngleSin);
                double segmentArea = 0.5 * radius * radius * (centralAngle - Math.Sin(centralAngle));

                if (!IsFinite(radius) || !IsFinite(segmentArea))
                {
                    return false;
                }

                signedArea += Math.Sign(bulge) * segmentArea;
                perimeter += radius * centralAngle;
            }

            area = Math.Abs(signedArea);
            return IsFinitePositive(area) && IsFinite(perimeter);
        }

        private static bool HasBulgedSegments(List<(double X, double Y, double Bulge)> vertices)
        {
            return vertices.Any(v => Math.Abs(v.Bulge) > BulgeEpsilon);
        }

        private static bool TryComputePlanarPolygonArea3d(List<Point3d> points, out double area)
        {
            area = 0.0;

            if (points.Count < 3 || !TryGetPolygonPlane(points, out Point3d origin, out Vector3d normal))
            {
                return false;
            }

            double scale = ComputePointScale(points);
            double planarityTolerance = Math.Max(GeometryEpsilon, scale * PlanarityRelativeTolerance);

            foreach (Point3d point in points)
            {
                double distanceToPlane = Math.Abs((point - origin).DotProduct(normal));
                if (distanceToPlane > planarityTolerance)
                {
                    return false;
                }
            }

            area = ComputePolygonArea3dNewell(points);
            return IsFinitePositive(area);
        }

        private static bool TryGetPolygonPlane(
            List<Point3d> points,
            out Point3d origin,
            out Vector3d normal)
        {
            origin = points[0];
            normal = new Vector3d();

            for (int i = 1; i < points.Count - 1; i++)
            {
                Vector3d a = points[i] - origin;
                if (a.Length <= GeometryEpsilon)
                {
                    continue;
                }

                for (int j = i + 1; j < points.Count; j++)
                {
                    Vector3d b = points[j] - origin;
                    if (b.Length <= GeometryEpsilon)
                    {
                        continue;
                    }

                    Vector3d cross = a.CrossProduct(b);
                    double minCrossLength = Math.Max(GeometryEpsilon, a.Length * b.Length * PlanarityRelativeTolerance);
                    if (cross.Length > minCrossLength)
                    {
                        normal = cross.GetNormal();
                        return true;
                    }
                }
            }

            return false;
        }

        private static double ComputePointScale(List<Point3d> points)
        {
            if (points.Count == 0)
            {
                return 1.0;
            }

            Point3d origin = points[0];
            double scale = 0.0;

            foreach (Point3d point in points)
            {
                scale = Math.Max(scale, (point - origin).Length);
            }

            return Math.Max(1.0, scale);
        }

        private static double ComputePolygonArea3dNewell(List<Point3d> points)
        {
            if (points.Count < 3)
            {
                return 0.0;
            }

            double nx = 0.0;
            double ny = 0.0;
            double nz = 0.0;

            for (int i = 0; i < points.Count; i++)
            {
                Point3d current = points[i];
                Point3d next = points[(i + 1) % points.Count];
                nx += (current.Y - next.Y) * (current.Z + next.Z);
                ny += (current.Z - next.Z) * (current.X + next.X);
                nz += (current.X - next.X) * (current.Y + next.Y);
            }

            return 0.5 * Math.Sqrt((nx * nx) + (ny * ny) + (nz * nz));
        }

        private static double ComputePolylineLength3d(List<Point3d> points, bool closed)
        {
            if (points.Count < 2)
            {
                return 0.0;
            }

            double length = 0.0;
            int segmentCount = closed ? points.Count : points.Count - 1;

            for (int i = 0; i < segmentCount; i++)
            {
                int j = (i + 1) % points.Count;
                length += points[i].DistanceTo(points[j]);
            }

            return length;
        }

        /// <summary>
        /// Calcula el area de un poligono simple usando la formula de Gauss (shoelace).
        /// Los vertices deben estar en orden secuencial y no representar curvas ni auto-intersecciones.
        /// </summary>
        private static double ComputePolygonArea(List<(double X, double Y)> points)
        {
            return Math.Abs(ComputeSignedPolygonArea(points));
        }

        private static double ComputeSignedPolygonArea(List<(double X, double Y)> points)
        {
            if (points.Count < 3)
            {
                return 0.0;
            }

            double doubleArea = 0.0;

            for (int i = 0; i < points.Count; i++)
            {
                int j = (i + 1) % points.Count;
                doubleArea += (points[i].X * points[j].Y) - (points[j].X * points[i].Y);
            }

            return 0.5 * doubleArea;
        }

        private static double ComputePolylineLength(List<(double X, double Y)> points, bool closed)
        {
            if (points.Count < 2)
            {
                return 0.0;
            }

            double length = 0.0;
            int segmentCount = closed ? points.Count : points.Count - 1;

            for (int i = 0; i < segmentCount; i++)
            {
                int j = (i + 1) % points.Count;
                double dx = points[j].X - points[i].X;
                double dy = points[j].Y - points[i].Y;
                length += Math.Sqrt((dx * dx) + (dy * dy));
            }

            return length;
        }

        private static bool IsAreaVertex(Vertex2d vertex)
        {
            return vertex.VertexType == Vertex2dType.SimpleVertex;
        }

        private static bool IsAreaVertex(PolylineVertex3d vertex)
        {
            return vertex.VertexType == Vertex3dType.SimpleVertex;
        }

        private static bool TryGetNativeCurveMetrics(Entity entity, out double area, out double perimeter)
        {
            area = 0.0;
            perimeter = 0.0;

            if (!(entity is Curve curve))
            {
                return false;
            }

            try
            {
                area = Math.Abs(curve.Area);
            }
            catch
            {
                return false;
            }

            TryGetLengthViaProperty(entity, out perimeter);
            perimeter = Math.Abs(perimeter);
            return IsFinitePositive(area) && IsFinite(perimeter);
        }

        private static bool TryGetAreaViaProperty(Entity entity, out double area)
        {
            area = 0.0;

            if (!SupportsNativeAreaProperty(entity))
            {
                return false;
            }

            try
            {
                var prop = entity.GetType().GetProperty("Area");
                if (prop == null)
                {
                    return false;
                }

                object value = prop.GetValue(entity, null);
                if (value == null)
                {
                    return false;
                }

                area = Convert.ToDouble(value);
                return IsFinitePositive(area);
            }
            catch
            {
                return false;
            }
        }

        private static string GetNativeAreaSource(Entity entity)
        {
            if (entity is Hatch hatch && hatch.HatchStyle == HatchStyle.Ignore)
            {
                return "native-area-property-hatch-ignore-style";
            }

            return "native-area-property";
        }

        private static bool TryGetLengthViaProperty(Entity entity, out double length)
        {
            length = 0.0;

            try
            {
                var prop = entity.GetType().GetProperty("Length");
                if (prop == null)
                {
                    return false;
                }

                object value = prop.GetValue(entity, null);
                if (value == null)
                {
                    return false;
                }

                length = Convert.ToDouble(value);
                return IsFinite(length);
            }
            catch
            {
                return false;
            }
        }

        private static bool TryGetEllipseArea(Entity entity, out double area, out double perimeter)
        {
            area = 0.0;
            perimeter = 0.0;

            if (!TryGetDoubleProperty(entity, "MajorRadius", out double majorRadius) ||
                !TryGetDoubleProperty(entity, "MinorRadius", out double minorRadius))
            {
                return false;
            }

            area = Math.PI * majorRadius * minorRadius;
            perimeter = ApproximateEllipsePerimeter(majorRadius, minorRadius);
            return IsFinitePositive(area);
        }

        private static double ApproximateEllipsePerimeter(double majorRadius, double minorRadius)
        {
            double h = Math.Pow(majorRadius - minorRadius, 2.0) /
                       Math.Pow(majorRadius + minorRadius, 2.0);

            return Math.PI * (majorRadius + minorRadius) *
                   (1.0 + ((3.0 * h) / (10.0 + Math.Sqrt(4.0 - (3.0 * h)))));
        }

        private static bool TryGetDoubleProperty(Entity entity, string propertyName, out double value)
        {
            value = 0.0;

            try
            {
                var prop = entity.GetType().GetProperty(propertyName);
                if (prop == null)
                {
                    return false;
                }

                object rawValue = prop.GetValue(entity, null);
                if (rawValue == null)
                {
                    return false;
                }

                value = Convert.ToDouble(rawValue);
                return IsFinite(value);
            }
            catch
            {
                return false;
            }
        }

        private static bool SupportsNativeAreaProperty(Entity entity)
        {
            string typeName = entity.GetType().Name;

            return typeName == "Hatch" ||
                   typeName == "Region" ||
                   typeName == "MPolygon" ||
                   typeName == "Ellipse" ||
                   typeName == "Solid" ||
                   typeName == "Trace";
        }

        private static string GetMeasurementKind(Entity entity)
        {
            string typeName = entity.GetType().Name;

            if (typeName == "Hatch" || typeName == "Region" || typeName == "MPolygon")
            {
                return "filled_surface";
            }

            if (typeName == "Ellipse")
            {
                return "analytic_curve";
            }

            return "native_area_property";
        }

        private static bool LooksLikeEllipse(Entity entity)
        {
            return entity.GetType().Name == "Ellipse";
        }

        private static PointData TryGetCenter(Entity entity)
        {
            try
            {
                Extents3d extents = entity.GeometricExtents;
                return new PointData
                {
                    X = (extents.MinPoint.X + extents.MaxPoint.X) / 2.0,
                    Y = (extents.MinPoint.Y + extents.MaxPoint.Y) / 2.0,
                    Z = (extents.MinPoint.Z + extents.MaxPoint.Z) / 2.0,
                };
            }
            catch
            {
                return null;
            }
        }

        private static AreaComputationMode GetAreaComputationMode()
        {
            return CachedAreaComputationMode.Value;
        }

        private static string GetAreaComputationModeName()
        {
            return GetAreaComputationMode().ToString().ToLowerInvariant();
        }

        private static AreaComputationMode LoadAreaComputationMode()
        {
            string modeValue = TryReadAreaModeValue();
            if (string.Equals(modeValue, "legacy", StringComparison.OrdinalIgnoreCase))
            {
                return AreaComputationMode.Legacy;
            }

            return AreaComputationMode.Improved;
        }

        private static string TryReadAreaModeValue()
        {
            try
            {
                string envValue = Environment.GetEnvironmentVariable("DUPLA_AREA_MODE");
                if (!string.IsNullOrWhiteSpace(envValue))
                {
                    return envValue.Trim();
                }

                string configPath = Path.Combine(Environment.CurrentDirectory, AreaModeConfigFileName);
                if (File.Exists(configPath))
                {
                    return File.ReadAllText(configPath).Trim();
                }
            }
            catch
            {
                // Default to improved when configuration cannot be read.
            }

            return "";
        }

        private static Editor TryGetEditor()
        {
            try
            {
                return Application.DocumentManager.MdiActiveDocument?.Editor;
            }
            catch
            {
                return null;
            }
        }

        private static string GetBlockName(Transaction tr, BlockReference br)
        {
            try
            {
                ObjectId recordId = br.IsDynamicBlock ? br.DynamicBlockTableRecord : br.BlockTableRecord;
                var record = tr.GetObject(recordId, OpenMode.ForRead) as BlockTableRecord;
                if (record != null && !string.IsNullOrWhiteSpace(record.Name))
                {
                    return record.Name;
                }
            }
            catch
            {
                // Fallback below.
            }

            try
            {
                return br.Name ?? "";
            }
            catch
            {
                return "";
            }
        }

        private static string SafeHandle(Entity entity)
        {
            try
            {
                return entity.Handle.ToString();
            }
            catch
            {
                return "";
            }
        }

        private static string SafeLayer(Entity entity)
        {
            try
            {
                return entity.Layer ?? "0";
            }
            catch
            {
                return "0";
            }
        }

        private static string GetSourceDrawingName(Database db)
        {
            try
            {
                return Path.GetFileName(db.Filename ?? "") ?? "";
            }
            catch
            {
                return "";
            }
        }

        private static double SafeLength(double length)
        {
            return IsFinite(length) ? Math.Abs(length) : 0.0;
        }

        private static bool IsFinitePositive(double value)
        {
            return IsFinite(value) && value > MinArea;
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }
    }
}
