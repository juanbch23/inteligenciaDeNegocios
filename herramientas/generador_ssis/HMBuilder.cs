using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.SqlServer.Dts.Runtime;
using Microsoft.SqlServer.Dts.Pipeline.Wrapper;
using Microsoft.SqlServer.Dts.Tasks.ExecuteSQLTask;
using Wrap = Microsoft.SqlServer.Dts.Runtime.Wrapper;

public class FfCol
{
    public string Name; public Wrap.DataType Type; public int Width; public bool Quoted;
    public FfCol(string n, Wrap.DataType t, int w = 0, bool q = false) { Name = n; Type = t; Width = w; Quoted = q; }
}

public class HMBuilder
{
    public const string Server = @"LAPTOP-IO596P6A\DEV";
    const string AdoType = "ADO.NET:System.Data.SqlClient.SqlConnection, System.Data, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089";

    // System.Data.DbType para parametros ADO.NET
    const int DbGuid = 9, DbInt32 = 11, DbString = 16, DbDateTime2 = 26;

    const string GetAuditSql =
@"INSERT INTO [DIM_AUDIT]
           ([TableName]
           ,[PkgName]
           ,[PkgGUID]
           ,[ExecStartDT]
           ,[ExecStopDT]
           ,[ExecutionInstanceGUID]
           ,[ExtractRowCnt]
           ,[TableInitialRowCnt]
           ,[TableFinalRowCnt]
           ,[SuccessfulProcessingInd])
     VALUES
           (@TableName
           ,@PkgName
           ,@PkgGUID
           ,@StartTime
           ,NULL
           ,@PkgExecGUID
           ,NULL
           ,@RowCount
           ,NULL
           ,'N')
SELECT CAST(SCOPE_IDENTITY() AS INT) AS AuditKey";

    const string UpdateAuditSql =
@"UPDATE [DIM_AUDIT]
SET ExecStopDT = SYSDATETIME()
 , ExtractRowCnt = @RowCount
 ,TableFinalRowCnt = @RowCount
 ,SuccessfulProcessingInd='Y'
WHERE AuditKey = @AuditKey;";

    const string MasterGetAuditSql =
@"INSERT INTO [DIM_AUDIT]
           ([TableName]
           ,[PkgName]
           ,[PkgGUID]
           ,[ExecStartDT]
           ,[ExecStopDT]
           ,[ExecutionInstanceGUID]
           ,[ExtractRowCnt]
           ,[TableInitialRowCnt]
           ,[TableFinalRowCnt]
           ,[SuccessfulProcessingInd])
     VALUES
           (@TableName
           ,@PkgName
           ,@PkgGUID
           ,@StartTime
           ,NULL
           ,@PkgExecGUID
           ,NULL
           ,NULL
           ,NULL
           ,'N')
SELECT CAST(SCOPE_IDENTITY() AS INT) AS AuditKey";

    const string MasterUpdateAuditSql =
@"UPDATE [DIM_AUDIT]
SET ExecStopDT = SYSDATETIME()
 ,SuccessfulProcessingInd='Y'
WHERE AuditKey = @AuditKey;";

    Project P;
    public List<string> Log = new List<string>();

    // ------------------------------------------------------------------ conexiones
    static string OleDbCs(string db) { return
        "Data Source=" + Server + ";Initial Catalog=" + db + ";Provider=MSOLEDBSQL19;Integrated Security=SSPI;Use Encryption for Data=Optional;Trust Server Certificate=True;Application Name=SSIS-H&M;Auto Translate=False;"; }
    static string AdoCs(string db) { return
        "Data Source=" + Server + ";Initial Catalog=" + db + ";Integrated Security=True;TrustServerCertificate=True;Application Name=SSIS-H&M;"; }

    ConnectionManager AddConn(string type, string name, string cs)
    {
        ConnectionManagerItem it = P.ConnectionManagerItems.Add(type, name + ".conmgr");
        ConnectionManager cm = it.ConnectionManager;
        cm.Name = name;
        cm.ConnectionString = cs;
        return cm;
    }

    ConnectionManager AddFlatFile(string name, string file, string folder, int codePage, string rowDelim, FfCol[] cols)
    {
        ConnectionManagerItem it = P.ConnectionManagerItems.Add("FLATFILE", name + ".conmgr");
        ConnectionManager cm = it.ConnectionManager;
        cm.Name = name;
        cm.ConnectionString = folder + "\\" + file;
        cm.Properties["Format"].SetValue(cm, "Delimited");
        cm.Properties["ColumnNamesInFirstDataRow"].SetValue(cm, true);
        cm.Properties["CodePage"].SetValue(cm, codePage);
        cm.Properties["Unicode"].SetValue(cm, false);
        cm.Properties["LocaleID"].SetValue(cm, 1033);           // punto decimal
        cm.Properties["TextQualifier"].SetValue(cm, "\"");
        cm.Properties["HeaderRowDelimiter"].SetValue(cm, rowDelim);   // articles/customers: LF, resto: CRLF
        Wrap.IDTSConnectionManagerFlatFile100 ff = (Wrap.IDTSConnectionManagerFlatFile100)cm.InnerObject;
        for (int i = 0; i < cols.Length; i++)
        {
            Wrap.IDTSConnectionManagerFlatFileColumn100 c = ff.Columns.Add();
            c.ColumnType = "Delimited";
            c.ColumnDelimiter = i == cols.Length - 1 ? rowDelim : ",";
            c.TextQualified = cols[i].Quoted;
            c.DataType = cols[i].Type;
            if (cols[i].Type == Wrap.DataType.DT_STR || cols[i].Type == Wrap.DataType.DT_WSTR)
            {
                c.MaximumWidth = cols[i].Width;
                c.ColumnWidth = 0;
            }
            ((Wrap.IDTSName100)c).Name = cols[i].Name;
        }
        cm.SetExpression("ConnectionString", "@[$Project::RutaDatos] + \"\\\\" + file + "\"");
        return cm;
    }

    // ------------------------------------------------------------------ paquetes y tareas
    Package NewPackage(string name, string tableName, bool master = false)
    {
        Package pkg = new Package();
        pkg.Name = name;
        pkg.ProtectionLevel = DTSProtectionLevel.DontSaveSensitive;
        pkg.Variables.Add("AuditKey", false, "User", 0);
        if (!master) pkg.Variables.Add("RowCount", false, "User", 0);
        pkg.Variables.Add("TableName", false, "User", tableName);
        P.PackageItems.Add(pkg, name + ".dtsx");
        return pkg;
    }

    static ConnectionManager C(Package pkg, string name)
    {
        foreach (ConnectionManager cm in pkg.Connections) if (cm.Name == name) return cm;
        throw new Exception("Conexion no encontrada en " + pkg.Name + ": " + name);
    }

    static void Param(ExecuteSQLTask t, string name, string variable, int dbType)
    {
        IDTSParameterBinding p = (IDTSParameterBinding)t.ParameterBindings.Add();
        p.ParameterName = name;
        p.DtsVariableName = variable;
        p.ParameterDirection = ParameterDirections.Input;
        p.DataType = dbType;
        p.ParameterSize = -1;
    }

    static TaskHost Sql(IDTSSequence parent, string name, ConnectionManager cm, string sql)
    {
        TaskHost th = (TaskHost)parent.Executables.Add("Microsoft.ExecuteSQLTask");
        th.Name = name;
        th.Description = "Tarea Ejecutar SQL";
        ExecuteSQLTask t = (ExecuteSQLTask)th.InnerObject;
        t.Connection = cm.ID;
        t.SqlStatementSource = sql;
        t.TimeOut = 0;
        return th;
    }

    static TaskHost RowCnt(Package pkg, string name, ConnectionManager cm, string table)
    {
        TaskHost th = Sql(pkg, name, cm, "SELECT COUNT(1) AS RowCnt FROM " + table);
        ExecuteSQLTask t = (ExecuteSQLTask)th.InnerObject;
        t.ResultSetType = ResultSetType.ResultSetType_SingleRow;
        IDTSResultBinding rb = (IDTSResultBinding)t.ResultSetBindings.Add();
        rb.ResultName = "0";
        rb.DtsVariableName = "User::RowCount";
        return th;
    }

    static TaskHost GetAuditKey(Package pkg, ConnectionManager adoDwh, bool master)
    {
        TaskHost th = Sql(pkg, "Task Get AuditKey", adoDwh, master ? MasterGetAuditSql : GetAuditSql);
        ExecuteSQLTask t = (ExecuteSQLTask)th.InnerObject;
        t.ResultSetType = ResultSetType.ResultSetType_SingleRow;
        IDTSResultBinding rb = (IDTSResultBinding)t.ResultSetBindings.Add();
        rb.ResultName = "0";
        rb.DtsVariableName = "User::AuditKey";
        Param(t, "StartTime", "System::StartTime", DbDateTime2);
        Param(t, "PkgName", "System::PackageName", DbString);
        Param(t, "PkgGUID", "System::PackageID", DbGuid);
        Param(t, "PkgExecGUID", "System::ExecutionInstanceGUID", DbGuid);
        Param(t, "TableName", "User::TableName", DbString);
        if (!master) Param(t, "RowCount", "User::RowCount", DbInt32);
        return th;
    }

    static TaskHost UpdateAudit(Package pkg, ConnectionManager adoDwh, bool master)
    {
        TaskHost th = Sql(pkg, "Update AuditDim", adoDwh, master ? MasterUpdateAuditSql : UpdateAuditSql);
        ExecuteSQLTask t = (ExecuteSQLTask)th.InnerObject;
        if (!master) Param(t, "RowCount", "User::RowCount", DbInt32);
        Param(t, "AuditKey", "User::AuditKey", DbInt32);
        return th;
    }

    static void Chain(Package pkg, params Executable[] steps)
    {
        for (int i = 1; i < steps.Length; i++) pkg.PrecedenceConstraints.Add(steps[i - 1], steps[i]);
    }

    // Plantilla del laboratorio: Prior RowCnt -> Get AuditKey -> [TRUNCATE] -> trabajo -> Post RowCnt -> Update AuditDim
    void Template(Package pkg, string targetConn, string countTable, string truncateSql, Executable work)
    {
        ConnectionManager adoDwh = C(pkg, "AdoNet DWH_HM");
        ConnectionManager target = C(pkg, targetConn);
        TaskHost prior = RowCnt(pkg, "Task Prior RowCnt", target, countTable);
        TaskHost key = GetAuditKey(pkg, adoDwh, false);
        TaskHost post = RowCnt(pkg, "Task Post RowCnt", target, countTable);
        TaskHost upd = UpdateAudit(pkg, adoDwh, false);
        if (truncateSql != null)
            Chain(pkg, prior, key, Sql(pkg, "TRUNCATE", target, truncateSql), work, post, upd);
        else
            Chain(pkg, prior, key, work, post, upd);
    }

    static MainPipe DataFlow(Package pkg, string name, out TaskHost th)
    {
        th = (TaskHost)pkg.Executables.Add("Microsoft.Pipeline");
        th.Name = name;
        th.Description = "Tarea Flujo de datos";
        try { th.Properties["AutoAdjustBufferSize"].SetValue(th, true); } catch { }
        return (MainPipe)th.InnerObject;
    }

    // ------------------------------------------------------------------ componentes del flujo de datos
    static IDTSComponentMetaData100 Comp(MainPipe mp, string classId, string name, out CManagedComponentWrapper d)
    {
        IDTSComponentMetaData100 c = mp.ComponentMetaDataCollection.New();
        c.ComponentClassID = classId;
        d = c.Instantiate();
        d.ProvideComponentProperties();
        c.Name = name;
        return c;
    }

    static void SetConn(IDTSComponentMetaData100 c, ConnectionManager cm)
    {
        c.RuntimeConnectionCollection[0].ConnectionManager = DtsConvert.GetExtendedInterface(cm);
        c.RuntimeConnectionCollection[0].ConnectionManagerID = cm.ID;
    }

    static void Refresh(CManagedComponentWrapper d)
    {
        d.AcquireConnections(null);
        d.ReinitializeMetaData();
        d.ReleaseConnections();
    }

    static void Connect(MainPipe mp, IDTSOutput100 from, IDTSComponentMetaData100 to)
    {
        IDTSPath100 path = mp.PathCollection.New();
        path.AttachPathAndPropagateNotifications(from, to.InputCollection[0]);
    }

    static IDTSOutput100 Out(IDTSComponentMetaData100 c, string name)
    {
        foreach (IDTSOutput100 o in c.OutputCollection) if (o.Name == name) return o;
        throw new Exception("Salida no encontrada: " + c.Name + "." + name);
    }

    // salida predeterminada de la division condicional (el nombre depende del idioma)
    static IDTSOutput100 DefaultOut(IDTSComponentMetaData100 c)
    {
        foreach (IDTSOutput100 o in c.OutputCollection) if (!o.IsErrorOut && o.Name != "bad") return o;
        throw new Exception("Sin salida predeterminada: " + c.Name);
    }

    static IDTSVirtualInputColumn100 VCol(IDTSVirtualInput100 vi, string name)
    {
        foreach (IDTSVirtualInputColumn100 v in vi.VirtualInputColumnCollection)
            if (string.Equals(v.Name, name, StringComparison.OrdinalIgnoreCase)) return v;
        throw new Exception("Columna no encontrada en la entrada: " + name);
    }

    static IDTSComponentMetaData100 OleSource(MainPipe mp, string name, ConnectionManager cm, string sql)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.OLEDBSource", name, out d);
        SetConn(c, cm);
        d.SetComponentProperty("AccessMode", 2);
        d.SetComponentProperty("SqlCommand", sql);
        Refresh(d);
        return c;
    }

    static IDTSComponentMetaData100 FlatSource(MainPipe mp, string name, ConnectionManager cm)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.FlatFileSource", name, out d);
        SetConn(c, cm);
        d.SetComponentProperty("RetainNulls", true);   // campos vacios -> NULL
        Refresh(d);
        return c;
    }

    static IDTSComponentMetaData100 ExcelSource(MainPipe mp, string name, ConnectionManager cm, string sheet)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.ExcelSource", name, out d);
        SetConn(c, cm);
        d.SetComponentProperty("AccessMode", 0);
        d.SetComponentProperty("OpenRowset", sheet);
        Refresh(d);
        return c;
    }

    // destino OLE DB en carga rapida; map = columna entrada -> columna destino (null = por nombre)
    static IDTSComponentMetaData100 OleDest(MainPipe mp, string name, ConnectionManager cm, string table,
                                            IDTSOutput100 from, Dictionary<string, string> map, bool big)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.OLEDBDestination", name, out d);
        SetConn(c, cm);
        d.SetComponentProperty("AccessMode", 3);
        d.SetComponentProperty("OpenRowset", table);
        d.SetComponentProperty("FastLoadKeepIdentity", false);
        d.SetComponentProperty("FastLoadKeepNulls", false);
        d.SetComponentProperty("FastLoadOptions", big ? "TABLOCK,CHECK_CONSTRAINTS,ROWS_PER_BATCH=1048576" : "TABLOCK,CHECK_CONSTRAINTS");
        d.SetComponentProperty("FastLoadMaxInsertCommitSize", big ? 1048576 : 2147483647);
        Refresh(d);
        Connect(mp, from, c);

        IDTSInput100 inp = c.InputCollection[0];
        IDTSVirtualInput100 vi = inp.GetVirtualInput();
        var ext = new Dictionary<string, IDTSExternalMetadataColumn100>(StringComparer.OrdinalIgnoreCase);
        foreach (IDTSExternalMetadataColumn100 e in inp.ExternalMetadataColumnCollection) ext[e.Name] = e;
        int mapped = 0;
        foreach (IDTSVirtualInputColumn100 v in vi.VirtualInputColumnCollection)
        {
            string target;
            if (map != null) { if (!map.TryGetValue(v.Name, out target)) continue; }
            else target = v.Name;
            IDTSExternalMetadataColumn100 e;
            if (!ext.TryGetValue(target, out e)) continue;
            IDTSInputColumn100 ic = d.SetUsageType(inp.ID, vi, v.LineageID, DTSUsageType.UT_READONLY);
            d.MapInputColumn(inp.ID, ic.ID, e.ID);
            mapped++;
        }
        if (map != null && mapped != map.Count)
            throw new Exception(name + ": se mapearon " + mapped + " de " + map.Count + " columnas");
        return c;
    }

    // Busqueda (full cache). outs: (columna de referencia, nombre de salida)
    static IDTSComponentMetaData100 Lookup(MainPipe mp, string name, ConnectionManager cm, string sql,
                                           IDTSOutput100 from, string[][] joins, string[][] outs, bool redirectNoMatch)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.Lookup", name, out d);
        SetConn(c, cm);
        d.SetComponentProperty("SqlCommand", sql);
        d.SetComponentProperty("CacheType", 0);                           // full cache
        d.SetComponentProperty("NoMatchBehavior", redirectNoMatch ? 1 : 0);
        Connect(mp, from, c);
        Refresh(d);

        IDTSInput100 inp = c.InputCollection[0];
        IDTSVirtualInput100 vi = inp.GetVirtualInput();
        foreach (string[] j in joins)
        {
            IDTSInputColumn100 ic = d.SetUsageType(inp.ID, vi, VCol(vi, j[0]).LineageID, DTSUsageType.UT_READONLY);
            d.SetInputColumnProperty(inp.ID, ic.ID, "JoinToReferenceColumn", j[1]);
        }
        IDTSOutput100 match = c.OutputCollection[0];
        foreach (string[] o in outs)
        {
            IDTSOutputColumn100 oc = d.InsertOutputColumnAt(match.ID, match.OutputColumnCollection.Count, o[1], "");
            d.SetOutputColumnProperty(match.ID, oc.ID, "CopyFromReferenceColumn", o[0]);
        }
        if (!redirectNoMatch)
        {
            // igual que el lab: "omitir error" -> la llave queda NULL y la division condicional la separa
            match.ErrorRowDisposition = DTSRowDisposition.RD_IgnoreFailure;
        }
        return c;
    }

    static string Lin(IDTSVirtualInput100 vi, string col) { return "#" + VCol(vi, col).LineageID; }

    // Division condicional: salida "bad" si alguna llave es NULL
    static IDTSComponentMetaData100 BadSplit(MainPipe mp, IDTSOutput100 from, string[] keys)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.ConditionalSplit", "División condicional", out d);
        Connect(mp, from, c);
        IDTSInput100 inp = c.InputCollection[0];
        IDTSVirtualInput100 vi = inp.GetVirtualInput();
        foreach (string k in keys) d.SetUsageType(inp.ID, vi, VCol(vi, k).LineageID, DTSUsageType.UT_READONLY);
        IDTSOutput100 bad = d.InsertOutput(DTSInsertPlacement.IP_BEFORE, c.OutputCollection[0].ID);
        bad.Name = "bad";
        bad.Description = "Filas con alguna llave sin coincidencia";
        bad.IsErrorOut = false;
        string expr = string.Join(" || ", keys.Select(k => "ISNULL(" + Lin(vi, k) + ")"));
        string friendly = string.Join(" || ", keys.Select(k => "ISNULL(" + k + ")"));
        d.SetOutputProperty(bad.ID, "Expression", expr);
        d.SetOutputProperty(bad.ID, "FriendlyExpression", friendly);
        d.SetOutputProperty(bad.ID, "EvaluationOrder", 0);
        return c;
    }

    // ================================================================== STAGE
    public void BuildStage(string ispac, string dataFolder)
    {
        P = Project.CreateProject();
        P.Name = "stage_H&M";
        P.ProtectionLevel = DTSProtectionLevel.DontSaveSensitive;
        Parameter rp = P.Parameters.Add("RutaDatos", TypeCode.String);
        rp.Value = dataFolder;
        rp.Description = "Carpeta con los CSV y el Excel de origen";

        AddConn("OLEDB", "OleDB STAGE_HM", OleDbCs("STAGE_HM"));
        AddConn(AdoType, "AdoNet STAGE_HM", AdoCs("STAGE_HM"));
        AddConn(AdoType, "AdoNet DWH_HM", AdoCs("DWH_HM"));

        var W = Wrap.DataType.DT_WSTR; var S = Wrap.DataType.DT_STR; var I4 = Wrap.DataType.DT_I4;
        var I2 = Wrap.DataType.DT_I2; var U1 = Wrap.DataType.DT_UI1; var R8 = Wrap.DataType.DT_R8; var D = Wrap.DataType.DT_DBDATE;

        AddFlatFile("FF articles", "articles.csv", dataFolder, 65001, "\n", new[] {
            new FfCol("article_id", I4), new FfCol("product_code", I4), new FfCol("prod_name", W, 100, true),
            new FfCol("product_type_no", I4), new FfCol("product_type_name", W, 50, true), new FfCol("product_group_name", W, 50, true),
            new FfCol("graphical_appearance_no", I4), new FfCol("graphical_appearance_name", W, 50, true),
            new FfCol("colour_group_code", I4), new FfCol("colour_group_name", W, 50, true),
            new FfCol("perceived_colour_value_id", I4), new FfCol("perceived_colour_value_name", W, 50, true),
            new FfCol("perceived_colour_master_id", I4), new FfCol("perceived_colour_master_name", W, 50, true),
            new FfCol("department_no", I4), new FfCol("department_name", W, 60, true),
            new FfCol("index_code", W, 5, true), new FfCol("index_name", W, 50, true),
            new FfCol("index_group_no", I4), new FfCol("index_group_name", W, 50, true),
            new FfCol("section_no", I4), new FfCol("section_name", W, 60, true),
            new FfCol("garment_group_no", I4), new FfCol("garment_group_name", W, 50, true),
            new FfCol("detail_desc", W, 1000, true) });
        AddFlatFile("FF customers", "customers.csv", dataFolder, 1252, "\n", new[] {
            new FfCol("customer_id", S, 64), new FfCol("FN", S, 5), new FfCol("Active", S, 5),
            new FfCol("club_member_status", S, 20), new FfCol("fashion_news_frequency", S, 20),
            new FfCol("age", I4), new FfCol("postal_code", S, 64) });
        AddFlatFile("FF transaction", "transaction.csv", dataFolder, 1252, "\r\n", new[] {
            new FfCol("t_dat", I4), new FfCol("customer_id", S, 64), new FfCol("article_id", I4),
            new FfCol("price", R8), new FfCol("sales_channel_id", U1), new FfCol("TemporadaID", U1) });
        AddFlatFile("FF DimFecha", "DimFecha.csv", dataFolder, 1252, "\r\n", new[] {
            new FfCol("FechaKey", I4), new FfCol("Fecha", D), new FfCol("Dia_Semana", U1), new FfCol("Nombre_Dia_Semana", S, 15),
            new FfCol("Dia_Mes", U1), new FfCol("Dia_Anio", I2), new FfCol("Nombre_Mes", S, 15), new FfCol("Mes_Anio", U1),
            new FfCol("Semana_Anio", U1), new FfCol("Anio", I2), new FfCol("Bimestre", U1), new FfCol("Trimestre", U1),
            new FfCol("Cuatrimestre", U1), new FfCol("Semestre", U1), new FfCol("Fin_Semana", U1) });
        AddFlatFile("FF Temporada", "Temporada.csv", dataFolder, 1252, "\r\n", new[] {
            new FfCol("TemporadaID", U1), new FfCol("Temporada", S, 30), new FfCol("FechaInicio", D), new FfCol("FechaFin", D) });

        ConnectionManager xl = AddConn("EXCEL", "Excel GoalsHyM",
            "Provider=Microsoft.ACE.OLEDB.16.0;Data Source=" + dataFolder + "\\GoalsHyM.xlsx;Extended Properties=\"Excel 12.0 XML;HDR=YES\";");
        xl.SetExpression("ExcelFilePath", "@[$Project::RutaDatos] + \"\\\\GoalsHyM.xlsx\"");

        StageFlat("StageArticles", "[HM].[StageArticles]", "FF articles", false);
        StageFlat("StageCustomers", "[HM].[StageCustomers]", "FF customers", false);
        StageFlat("StageTransactions", "[HM].[StageTransactions]", "FF transaction", true);
        StageFlat("StageFecha", "[HM].[StageFecha]", "FF DimFecha", false);
        StageFlat("StageTemporada", "[HM].[StageTemporada]", "FF Temporada", false);

        {   // Excel -> StageGoals
            Package pkg = NewPackage("StageGoals", "[HM].[StageGoals]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "DF StageGoals", out th);
            var src = ExcelSource(mp, "Origen de Excel", C(pkg, "Excel GoalsHyM"), "Hoja1$");
            OleDest(mp, "StageGoals", C(pkg, "OleDB STAGE_HM"), "[HM].[StageGoals]", src.OutputCollection[0],
                new Dictionary<string, string> {
                    { "Escenario", "Escenario" }, { "Monto", "Monto" }, { "department_name", "department_name" },
                    { "section_name", "section_name" }, { "TemporadaID", "TemporadaID" }, { "AÑO MES", "AnioMes" } }, false);
            Template(pkg, "AdoNet STAGE_HM", "[HM].[StageGoals]", "TRUNCATE TABLE [HM].[StageGoals];", th);
        }

        Master("MasterExecuteStage", "Master_Stage_HM", new[] { "Contenedor de secuencias" },
            new[] { new[] { "StageArticles", "StageCustomers", "StageTransactions", "StageFecha", "StageTemporada", "StageGoals" } },
            null);
        P.SaveTo(ispac);
        P.Dispose();
    }

    void StageFlat(string pkgName, string table, string ff, bool big)
    {
        Package pkg = NewPackage(pkgName, table);
        TaskHost th; MainPipe mp = DataFlow(pkg, "DF " + pkgName, out th);
        var src = FlatSource(mp, "Origen de archivo plano", C(pkg, ff));
        OleDest(mp, pkgName, C(pkg, "OleDB STAGE_HM"), table, src.OutputCollection[0], null, big);
        Template(pkg, "AdoNet STAGE_HM", table, "TRUNCATE TABLE " + table + ";", th);
    }

    // ================================================================== DWH
    public void BuildDwh(string ispac)
    {
        P = Project.CreateProject();
        P.Name = "DWH_H&M";
        P.ProtectionLevel = DTSProtectionLevel.DontSaveSensitive;

        AddConn("OLEDB", "OleDB DWH_HM", OleDbCs("DWH_HM"));
        AddConn("OLEDB", "OleDB STAGE_HM", OleDbCs("STAGE_HM"));
        AddConn(AdoType, "AdoNet DWH_HM", AdoCs("DWH_HM"));

        foreach (string dim in new[] { "DimTemporada", "DimCanal", "DimDepartamento", "DimArticulo", "DimCliente" })
        {
            string table = "[Ventas].[" + dim + "]";
            Package pkg = NewPackage(dim, table);
            TaskHost sp = Sql(pkg, "Execute sp_" + dim, C(pkg, "AdoNet DWH_HM"), "EXEC [Ventas].[sp_" + dim + "];");
            Template(pkg, "AdoNet DWH_HM", table, null, sp);
        }

        {   // DimFecha: incremental, corrige Fin_Semana
            Package pkg = NewPackage("DimFecha", "[GENERICO].[DimFecha]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "DIM FECHA", out th);
            var src = OleSource(mp, "Origen de OLE DB", C(pkg, "OleDB STAGE_HM"),
@"SELECT [FechaKey], [Fecha], [Dia_Semana], [Nombre_Dia_Semana], [Dia_Mes], [Dia_Anio], [Nombre_Mes],
       [Mes_Anio], [Semana_Anio], [Anio], [Bimestre], [Trimestre], [Cuatrimestre], [Semestre]
  FROM [HM].[StageFecha]");
            CManagedComponentWrapper dd;
            var dc = Comp(mp, "Microsoft.DerivedColumn", "Columna derivada Fin_Semana", out dd);
            Connect(mp, src.OutputCollection[0], dc);
            IDTSInput100 dcIn = dc.InputCollection[0];
            IDTSVirtualInput100 dcVi = dcIn.GetVirtualInput();
            dd.SetUsageType(dcIn.ID, dcVi, VCol(dcVi, "Dia_Semana").LineageID, DTSUsageType.UT_READONLY);
            IDTSOutputColumn100 oc = dd.InsertOutputColumnAt(dc.OutputCollection[0].ID, 0, "Fin_Semana", "1 = sabado o domingo");
            dd.SetOutputColumnDataTypeProperties(dc.OutputCollection[0].ID, oc.ID, Wrap.DataType.DT_UI1, 0, 0, 0, 0);
            string lin = Lin(dcVi, "Dia_Semana");
            dd.SetOutputColumnProperty(dc.OutputCollection[0].ID, oc.ID, "Expression",
                "(" + lin + " == 1 || " + lin + " == 7) ? (DT_UI1)1 : (DT_UI1)0");
            dd.SetOutputColumnProperty(dc.OutputCollection[0].ID, oc.ID, "FriendlyExpression",
                "(Dia_Semana == 1 || Dia_Semana == 7) ? (DT_UI1)1 : (DT_UI1)0");

            var lk = Lookup(mp, "Existe en DimFecha", C(pkg, "OleDB DWH_HM"), "SELECT [FechaKey] FROM [GENERICO].[DimFecha]",
                dc.OutputCollection[0], new[] { new[] { "FechaKey", "FechaKey" } }, new string[0][], true);
            OleDest(mp, "DimFecha", C(pkg, "OleDB DWH_HM"), "[GENERICO].[DimFecha]",
                lk.OutputCollection[1], null, false);
            Template(pkg, "AdoNet DWH_HM", "[GENERICO].[DimFecha]", null, th);
        }

        {   // FactVentas
            Package pkg = NewPackage("FactVentas", "[Ventas].[FactVentas]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "FACT VENTAS", out th);
            ConnectionManager dwh = C(pkg, "OleDB DWH_HM");
            var src = OleSource(mp, "Origen de OLE DB", C(pkg, "OleDB STAGE_HM"),
@"SELECT [t_dat], [customer_id], [article_id], [price], [sales_channel_id], [TemporadaID],
       CAST([price] AS DECIMAL(19,6)) AS [Precio]
  FROM [HM].[StageTransactions]");
            var l1 = Lookup(mp, "DimFecha", dwh, "SELECT [FechaKey] FROM [GENERICO].[DimFecha]", src.OutputCollection[0],
                new[] { new[] { "t_dat", "FechaKey" } }, new[] { new[] { "FechaKey", "FechaKey" } }, false);
            var l2 = Lookup(mp, "DimCliente", dwh, "SELECT [ClienteKey], [CustomerID] FROM [Ventas].[DimCliente]", l1.OutputCollection[0],
                new[] { new[] { "customer_id", "CustomerID" } }, new[] { new[] { "ClienteKey", "ClienteKey" } }, false);
            var l3 = Lookup(mp, "DimArticulo", dwh, "SELECT [ArticuloKey], [DepartamentoKey], [ArticleID] FROM [Ventas].[DimArticulo]", l2.OutputCollection[0],
                new[] { new[] { "article_id", "ArticleID" } },
                new[] { new[] { "ArticuloKey", "ArticuloKey" }, new[] { "DepartamentoKey", "DepartamentoKey" } }, false);
            var l4 = Lookup(mp, "DimCanal", dwh, "SELECT [CanalKey], [CanalID] FROM [Ventas].[DimCanal]", l3.OutputCollection[0],
                new[] { new[] { "sales_channel_id", "CanalID" } }, new[] { new[] { "CanalKey", "CanalKey" } }, false);
            var l5 = Lookup(mp, "DimTemporada", dwh, "SELECT [TemporadaKey], [TemporadaID] FROM [Ventas].[DimTemporada]", l4.OutputCollection[0],
                new[] { new[] { "TemporadaID", "TemporadaID" } }, new[] { new[] { "TemporadaKey", "TemporadaKey" } }, false);
            var keys = new[] { "FechaKey", "ClienteKey", "ArticuloKey", "DepartamentoKey", "CanalKey", "TemporadaKey" };
            var cs = BadSplit(mp, l5.OutputCollection[0], keys);
            OleDest(mp, "ErrorFactVentas", dwh, "[Ventas].[ErrorFactVentas]", Out(cs, "bad"), null, false);
            var factMap = keys.ToDictionary(k => k, k => k); factMap["Precio"] = "Precio";
            OleDest(mp, "FactVentas", dwh, "[Ventas].[FactVentas]", DefaultOut(cs), factMap, true);
            Template(pkg, "AdoNet DWH_HM", "[Ventas].[FactVentas]",
                "TRUNCATE TABLE [Ventas].[FactVentas];\r\nTRUNCATE TABLE [Ventas].[ErrorFactVentas];", th);
        }

        {   // FactMetas (GoalsHyM.xlsx)
            Package pkg = NewPackage("FactMetas", "[Ventas].[FactMetas]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "FACT METAS", out th);
            ConnectionManager dwh = C(pkg, "OleDB DWH_HM");
            var src = OleSource(mp, "Origen de OLE DB", C(pkg, "OleDB STAGE_HM"),
@"SELECT CAST([Escenario] AS NVARCHAR(30))       AS [Escenario],
       [Monto],
       CAST([Monto] AS DECIMAL(19,6))            AS [MontoDec],
       CAST([department_name] AS NVARCHAR(60))   AS [department_name],
       CAST([section_name] AS NVARCHAR(60))      AS [section_name],
       CAST([TemporadaID] AS TINYINT)            AS [TemporadaID],
       CAST([AnioMes] AS INT)                    AS [AnioMes]
  FROM [HM].[StageGoals]");
            var l1 = Lookup(mp, "DimDepartamento", dwh, "SELECT [DepartamentoKey], [department_name], [section_name] FROM [Ventas].[DimDepartamento]",
                src.OutputCollection[0], new[] { new[] { "department_name", "department_name" }, new[] { "section_name", "section_name" } },
                new[] { new[] { "DepartamentoKey", "DepartamentoKey" } }, false);
            var l2 = Lookup(mp, "DimTemporada", dwh, "SELECT [TemporadaKey], [TemporadaID] FROM [Ventas].[DimTemporada]", l1.OutputCollection[0],
                new[] { new[] { "TemporadaID", "TemporadaID" } }, new[] { new[] { "TemporadaKey", "TemporadaKey" } }, false);
            var l3 = Lookup(mp, "DimFecha (mes)", dwh,
                "SELECT MIN([FechaKey]) AS [FechaKey], [AnioMes] FROM [GENERICO].[DimFecha] WHERE [FechaKey] > 0 GROUP BY [AnioMes]",
                l2.OutputCollection[0], new[] { new[] { "AnioMes", "AnioMes" } }, new[] { new[] { "FechaKey", "FechaKey" } }, false);
            var keys = new[] { "DepartamentoKey", "TemporadaKey", "FechaKey" };
            var cs = BadSplit(mp, l3.OutputCollection[0], keys);
            OleDest(mp, "ErrorFactMetas", dwh, "[Ventas].[ErrorFactMetas]", Out(cs, "bad"), null, false);
            OleDest(mp, "FactMetas", dwh, "[Ventas].[FactMetas]", DefaultOut(cs),
                new Dictionary<string, string> {
                    { "Escenario", "Escenario" }, { "FechaKey", "FechaKey" }, { "AnioMes", "AnioMes" },
                    { "DepartamentoKey", "DepartamentoKey" }, { "TemporadaKey", "TemporadaKey" }, { "MontoDec", "Monto" } }, false);
            Template(pkg, "AdoNet DWH_HM", "[Ventas].[FactMetas]",
                "TRUNCATE TABLE [Ventas].[FactMetas];\r\nTRUNCATE TABLE [Ventas].[ErrorFactMetas];", th);
        }

        Master("MasterExecuteDWH", "Master_DWH_HM", new[] { "Dimensiones", "Hechos" },
            new[] { new[] { "DimFecha", "DimTemporada", "DimCanal", "DimDepartamento", "DimArticulo", "DimCliente" },
                    new[] { "FactVentas", "FactMetas" } },
            new[] { new[] { "DimDepartamento", "DimArticulo" } });   // DimArticulo necesita DepartamentoKey
        P.SaveTo(ispac);
        P.Dispose();
    }

    // ================================================================== MAESTROS (proceso_bi parte 2)
    void Master(string name, string tableName, string[] containers, string[][] packages, string[][] inner)
    {
        Package pkg = NewPackage(name, tableName, true);
        ConnectionManager adoDwh = C(pkg, "AdoNet DWH_HM");
        Executable prev = GetAuditKey(pkg, adoDwh, true);
        for (int i = 0; i < containers.Length; i++)
        {
            Sequence seq = (Sequence)pkg.Executables.Add("STOCK:SEQUENCE");
            seq.Name = containers[i];
            var tasks = new Dictionary<string, TaskHost>();
            foreach (string p in packages[i])
            {
                TaskHost th = (TaskHost)seq.Executables.Add("Microsoft.ExecutePackageTask");
                th.Name = p;
                th.Description = "Tarea Ejecutar paquete";
                th.Properties["UseProjectReference"].SetValue(th, true);
                th.Properties["PackageName"].SetValue(th, p + ".dtsx");
                tasks[p] = th;
            }
            if (inner != null)
                foreach (string[] pair in inner)
                    if (tasks.ContainsKey(pair[0]) && tasks.ContainsKey(pair[1]))
                        seq.PrecedenceConstraints.Add(tasks[pair[0]], tasks[pair[1]]);
            pkg.PrecedenceConstraints.Add(prev, seq);
            prev = seq;
        }
        pkg.PrecedenceConstraints.Add(prev, UpdateAudit(pkg, adoDwh, true));
    }
}
