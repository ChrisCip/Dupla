using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;

namespace DuplaDwgDump
{
    internal static class Program
    {
        private const string AutoCadRoot = @"C:\Program Files\Autodesk\AutoCAD 2027";

        private static int Main(string[] args)
        {
            AssemblyLoadContext.Default.Resolving += ResolveAutodeskAssembly;

            if (args.Length < 1)
            {
                Console.Error.WriteLine("Usage: DuplaDwgDump <input.dwg> [output.json]");
                return 2;
            }

            string inputPath = Path.GetFullPath(args[0]);
            string outputPath = args.Length > 1 ? Path.GetFullPath(args[1]) : Path.Combine(Environment.CurrentDirectory, "resultados.json");

            if (!File.Exists(inputPath))
            {
                Console.Error.WriteLine("DWG not found: " + inputPath);
                return 3;
            }

            var results = new Dictionary<string, object>();
            var entities = new List<object>();

            using (var db = new Database(false, true))
            {
                db.ReadDwgFile(inputPath, FileOpenMode.OpenForReadAndAllShare, true, null);
                db.CloseInput(true);

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

                        var serialized = SerializeEntity(ent, tr);
                        if (serialized != null)
                        {
                            entities.Add(serialized);
                        }
                    }

                    tr.Commit();
                }

                results["UnitsToMmFactor"] = UnitsToMmFactor(db);
            }

            results["EntityCount"] = entities.Count;
            results["Entities"] = entities;
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? Environment.CurrentDirectory);
            File.WriteAllText(outputPath, JsonSerializer.Serialize(results, new JsonSerializerOptions()));
            Console.WriteLine(outputPath);
            return 0;
        }

        private static Assembly ResolveAutodeskAssembly(AssemblyLoadContext context, AssemblyName assemblyName)
        {
            string candidate = Path.Combine(AutoCadRoot, assemblyName.Name + ".dll");
            if (File.Exists(candidate))
            {
                return context.LoadFromAssemblyPath(candidate);
            }
            return null;
        }

        private static Dictionary<string, object> SerializeEntity(Entity ent, Transaction tr)
        {
            var payload = new Dictionary<string, object>
            {
                ["Handle"] = ent.Handle.ToString(),
                ["Layer"] = ent.Layer ?? "0",
                ["Type"] = ent.GetType().Name,
            };

            var bounds = TryGetBounds(ent);
            if (bounds != null)
            {
                payload["Bounds"] = bounds;
            }

            if (ent is BlockReference blockRef)
            {
                payload["Name"] = GetBlockName(blockRef, tr);
                payload["Attributes"] = GetBlockAttributes(blockRef, tr);
                payload["Position"] = PointDict(blockRef.Position);
                payload["Rotation"] = blockRef.Rotation;
                return payload;
            }

            if (ent is Polyline polyline)
            {
                payload["Closed"] = polyline.Closed;
                payload["Area"] = polyline.Closed ? polyline.Area : 0.0;
                payload["Length"] = polyline.Length;
                payload["Elevation"] = polyline.Elevation;
                payload["Vertices"] = GetPolylineVertices(polyline);
                return payload;
            }

            if (ent is Polyline2d polyline2d)
            {
                payload["Closed"] = polyline2d.Closed;
                payload["Vertices"] = GetPolyline2dVertices(polyline2d, tr);
                return payload;
            }

            if (ent is Polyline3d polyline3d)
            {
                payload["Closed"] = polyline3d.Closed;
                payload["Vertices"] = GetPolyline3dVertices(polyline3d, tr);
                return payload;
            }

            if (ent is Circle circle)
            {
                payload["Center"] = PointDict(circle.Center);
                payload["Radius"] = circle.Radius;
                return payload;
            }

            if (ent is Arc arc)
            {
                payload["Center"] = PointDict(arc.Center);
                payload["Radius"] = arc.Radius;
                payload["StartAngle"] = arc.StartAngle;
                payload["EndAngle"] = arc.EndAngle;
                return payload;
            }

            if (ent is Line line)
            {
                payload["StartPoint"] = PointDict(line.StartPoint);
                payload["EndPoint"] = PointDict(line.EndPoint);
                return payload;
            }

            return payload;
        }

        private static Dictionary<string, object> GetBlockAttributes(BlockReference blockRef, Transaction tr)
        {
            var props = new Dictionary<string, object>();
            foreach (ObjectId attId in blockRef.AttributeCollection)
            {
                var att = tr.GetObject(attId, OpenMode.ForRead) as AttributeReference;
                if (att != null)
                {
                    props[att.Tag] = att.TextString ?? string.Empty;
                }
            }
            return props;
        }

        private static string GetBlockName(BlockReference blockRef, Transaction tr)
        {
            try
            {
                var btrRef = (BlockTableRecord)tr.GetObject(blockRef.DynamicBlockTableRecord, OpenMode.ForRead);
                return btrRef.Name;
            }
            catch
            {
                return blockRef.Name;
            }
        }

        private static List<Dictionary<string, object>> GetPolylineVertices(Polyline polyline)
        {
            var vertices = new List<Dictionary<string, object>>();
            for (int i = 0; i < polyline.NumberOfVertices; i++)
            {
                vertices.Add(PointDict(polyline.GetPoint3dAt(i)));
            }
            return vertices;
        }

        private static List<Dictionary<string, object>> GetPolyline2dVertices(Polyline2d polyline, Transaction tr)
        {
            var vertices = new List<Dictionary<string, object>>();
            foreach (ObjectId vertexId in polyline)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as Vertex2d;
                if (vertex != null)
                {
                    vertices.Add(PointDict(vertex.Position));
                }
            }
            return vertices;
        }

        private static List<Dictionary<string, object>> GetPolyline3dVertices(Polyline3d polyline, Transaction tr)
        {
            var vertices = new List<Dictionary<string, object>>();
            foreach (ObjectId vertexId in polyline)
            {
                var vertex = tr.GetObject(vertexId, OpenMode.ForRead) as PolylineVertex3d;
                if (vertex != null)
                {
                    vertices.Add(PointDict(vertex.Position));
                }
            }
            return vertices;
        }

        private static Dictionary<string, object> TryGetBounds(Entity ent)
        {
            try
            {
                var extents = ent.GeometricExtents;
                return new Dictionary<string, object>
                {
                    ["Min"] = PointDict(extents.MinPoint),
                    ["Max"] = PointDict(extents.MaxPoint),
                };
            }
            catch
            {
                return null;
            }
        }

        private static Dictionary<string, object> PointDict(Point3d point)
        {
            return new Dictionary<string, object>
            {
                ["X"] = point.X,
                ["Y"] = point.Y,
                ["Z"] = point.Z,
            };
        }

        private static double UnitsToMmFactor(Database db)
        {
            switch (db.Insunits)
            {
                case UnitsValue.Inches:
                    return 25.4;
                case UnitsValue.Feet:
                    return 304.8;
                case UnitsValue.Miles:
                    return 1609344.0;
                case UnitsValue.Millimeters:
                    return 1.0;
                case UnitsValue.Centimeters:
                    return 10.0;
                case UnitsValue.Meters:
                    return 1000.0;
                case UnitsValue.Kilometers:
                    return 1000000.0;
                case UnitsValue.Mils:
                    return 0.0254;
                case UnitsValue.Yards:
                    return 914.4;
                case UnitsValue.Angstroms:
                    return 0.0000001;
                case UnitsValue.Nanometers:
                    return 0.000001;
                case UnitsValue.Microns:
                    return 0.001;
                case UnitsValue.Decimeters:
                    return 100.0;
                case UnitsValue.Hectometers:
                    return 100000.0;
                case UnitsValue.Gigameters:
                    return 1000000000000.0;
                case UnitsValue.Astronomical:
                    return 149597870700000.0;
                case UnitsValue.LightYears:
                    return 9460730472580800000.0;
                case UnitsValue.Parsecs:
                    return 30856775814671900000.0;
                default:
                    return 1.0;
            }
        }
    }
}
