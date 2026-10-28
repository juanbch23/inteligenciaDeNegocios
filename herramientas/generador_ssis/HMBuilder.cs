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

    // Mismo UPDATE del laboratorio, dentro de un SP que ademas registra duplicados y filas con error
    const string UpdateAuditSql =
@"EXEC [dbo].[sp_CerrarAuditoria] @AuditKey = @AuditKey, @RowCount = @RowCount;";

    // Controlador OnError: si el paquete falla, la auditoria queda en 'N' con el mensaje del error
    const string OnErrorAuditSql =
@"UPDATE [DIM_AUDIT]
SET ExecStopDT = SYSDATETIME()
 ,SuccessfulProcessingInd = 'N'
 ,MensajeError = LEFT(ISNULL(MensajeError + N' | ', N'') + @Mensaje, 2000)
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
        OnErrorAudit(pkg, adoDwh);
    }

    static void OnErrorAudit(Package pkg, ConnectionManager adoDwh)
    {
        DtsEventHandler eh = (DtsEventHandler)pkg.EventHandlers.Add("OnError");
        TaskHost th = Sql(eh, "Registrar error en DIM_AUDIT", adoDwh, OnErrorAuditSql);
        th.DisableEventHandlers = true;   // si esta tarea fallara, que no se dispare otra vez el OnError
        ExecuteSQLTask t = (ExecuteSQLTask)th.InnerObject;
        Param(t, "Mensaje", "System::ErrorDescription", DbString);
        Param(t, "AuditKey", "User::AuditKey", DbInt32);
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
        // dato sucio nunca detiene la carga: un valor mas largo que la columna se recorta (y luego
        // falla la validacion del DWH con su motivo) en vez de hacer fallar el paquete
        foreach (IDTSOutputColumn100 oc in c.OutputCollection[0].OutputColumnCollection)
        {
            oc.TruncationRowDisposition = DTSRowDisposition.RD_IgnoreFailure;
            oc.ErrorRowDisposition = DTSRowDisposition.RD_IgnoreFailure;
        }
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

    // Division condicional: salida "bad" si la consulta de origen puso un MotivoDescarte o si alguna llave es NULL
    static IDTSComponentMetaData100 BadSplit(MainPipe mp, IDTSOutput100 from, string[] keys)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.ConditionalSplit", "División condicional", out d);
        Connect(mp, from, c);
        IDTSInput100 inp = c.InputCollection[0];
        IDTSVirtualInput100 vi = inp.GetVirtualInput();
        foreach (string k in keys) d.SetUsageType(inp.ID, vi, VCol(vi, k).LineageID, DTSUsageType.UT_READONLY);
        d.SetUsageType(inp.ID, vi, VCol(vi, "MotivoDescarte").LineageID, DTSUsageType.UT_READONLY);
        IDTSOutput100 bad = d.InsertOutput(DTSInsertPlacement.IP_BEFORE, c.OutputCollection[0].ID);
        bad.Name = "bad";
        bad.Description = "Filas con dato invalido o con alguna llave sin coincidencia";
        bad.IsErrorOut = false;
        string expr = "!ISNULL(" + Lin(vi, "MotivoDescarte") + ") || " + string.Join(" || ", keys.Select(k => "ISNULL(" + Lin(vi, k) + ")"));
        string friendly = "!ISNULL(MotivoDescarte) || " + string.Join(" || ", keys.Select(k => "ISNULL(" + k + ")"));
        d.SetOutputProperty(bad.ID, "Expression", expr);
        d.SetOutputProperty(bad.ID, "FriendlyExpression", friendly);
        d.SetOutputProperty(bad.ID, "EvaluationOrder", 0);
        return c;
    }

    // Columna derivada "Motivo" para la tabla de error: el motivo de la consulta de origen o,
    // si no hay, la primera llave sin coincidencia. motivos = (llave, texto)
    static IDTSComponentMetaData100 MotivoColumn(MainPipe mp, IDTSOutput100 from, string[][] motivos)
    {
        CManagedComponentWrapper d;
        IDTSComponentMetaData100 c = Comp(mp, "Microsoft.DerivedColumn", "Columna derivada Motivo", out d);
        Connect(mp, from, c);
        IDTSInput100 inp = c.InputCollection[0];
        IDTSVirtualInput100 vi = inp.GetVirtualInput();
        d.SetUsageType(inp.ID, vi, VCol(vi, "MotivoDescarte").LineageID, DTSUsageType.UT_READONLY);
        foreach (string[] m in motivos) d.SetUsageType(inp.ID, vi, VCol(vi, m[0]).LineageID, DTSUsageType.UT_READONLY);
        string expr = "(DT_WSTR,200)\"Llave sin coincidencia en una dimensión\"", friendly = expr;
        for (int i = motivos.Length - 1; i >= 0; i--)
        {
            string txt = "(DT_WSTR,200)\"" + motivos[i][1] + "\"";
            expr = "(ISNULL(" + Lin(vi, motivos[i][0]) + ") ? " + txt + " : " + expr + ")";
            friendly = "(ISNULL(" + motivos[i][0] + ") ? " + txt + " : " + friendly + ")";
        }
        IDTSOutput100 o = c.OutputCollection[0];
        IDTSOutputColumn100 oc = d.InsertOutputColumnAt(o.ID, 0, "Motivo", "Motivo del descarte");
        d.SetOutputColumnDataTypeProperties(o.ID, oc.ID, Wrap.DataType.DT_WSTR, 200, 0, 0, 0);
        d.SetOutputColumnProperty(o.ID, oc.ID, "Expression",
            "ISNULL(" + Lin(vi, "MotivoDescarte") + ") ? " + expr + " : " + Lin(vi, "MotivoDescarte"));
        d.SetOutputColumnProperty(o.ID, oc.ID, "FriendlyExpression", "ISNULL(MotivoDescarte) ? " + friendly + " : MotivoDescarte");
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

        // Todas las columnas como TEXTO (igual que las tablas del STAGE): un dato sucio no hace fallar la carga.
        // La conversion de tipos y la validacion se hacen al pasar al DWH (TRY_CONVERT + tablas de error).
        var W = Wrap.DataType.DT_WSTR; var S = Wrap.DataType.DT_STR;
        Func<Wrap.DataType, int, string[], FfCol[]> Txt = (t, w, names) => names.Select(n => new FfCol(n, t, w, true)).ToArray();

        AddFlatFile("FF articles", "articles.csv", dataFolder, 65001, "\n", new[] {
            new FfCol("article_id", W, 100, true), new FfCol("product_code", W, 100, true), new FfCol("prod_name", W, 200, true),
            new FfCol("product_type_no", W, 100, true), new FfCol("product_type_name", W, 200, true), new FfCol("product_group_name", W, 200, true),
            new FfCol("graphical_appearance_no", W, 100, true), new FfCol("graphical_appearance_name", W, 200, true),
            new FfCol("colour_group_code", W, 100, true), new FfCol("colour_group_name", W, 200, true),
            new FfCol("perceived_colour_value_id", W, 100, true), new FfCol("perceived_colour_value_name", W, 200, true),
            new FfCol("perceived_colour_master_id", W, 100, true), new FfCol("perceived_colour_master_name", W, 200, true),
            new FfCol("department_no", W, 100, true), new FfCol("department_name", W, 200, true),
            new FfCol("index_code", W, 100, true), new FfCol("index_name", W, 200, true),
            new FfCol("index_group_no", W, 100, true), new FfCol("index_group_name", W, 200, true),
            new FfCol("section_no", W, 100, true), new FfCol("section_name", W, 200, true),
            new FfCol("garment_group_no", W, 100, true), new FfCol("garment_group_name", W, 200, true),
            new FfCol("detail_desc", W, 2000, true) });
        AddFlatFile("FF customers", "customers.csv", dataFolder, 1252, "\n",
            Txt(S, 100, new[] { "customer_id", "FN", "Active", "club_member_status", "fashion_news_frequency", "age", "postal_code" }));
        AddFlatFile("FF transaction", "transaction.csv", dataFolder, 1252, "\r\n",
            Txt(S, 100, new[] { "t_dat", "customer_id", "article_id", "price", "sales_channel_id", "TemporadaID" }));
        AddFlatFile("FF DimFecha", "DimFecha.csv", dataFolder, 1252, "\r\n",
            Txt(S, 100, new[] { "FechaKey", "Fecha", "Dia_Semana", "Nombre_Dia_Semana", "Dia_Mes", "Dia_Anio", "Nombre_Mes", "Mes_Anio",
                                "Semana_Anio", "Anio", "Bimestre", "Trimestre", "Cuatrimestre", "Semestre", "Fin_Semana" }));
        AddFlatFile("FF Temporada", "Temporada.csv", dataFolder, 1252, "\r\n",
            Txt(S, 100, new[] { "TemporadaID", "Temporada", "FechaInicio", "FechaFin" }));

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

    // ================================================================== consultas de origen con limpieza
    // Estrategia (indicaciones del profesor):
    //   - lineas identicas -> se conserva UNA (GROUP BY de la linea completa; LineasOrigen = cuantas venian)
    //   - TRY_CONVERT: un valor que no sirve devuelve NULL en vez de detener la carga
    //   - sin supuestos: un dato que no sirve NO se rellena; va a la tabla de error con MotivoDescarte
    //   - price x 40000 con 4 decimales, tal como viene (0 o negativo se carga igual: puede ser oferta o devolucion)
    //   - REGLA del precio: la coma se toma como separador decimal ("1184,74" y "1,184" -> 1184.74 y 1.184)
    //   - REGLA de fechas con '/': dia/mes/anio como en el Peru (01/02/2019 = 1 de febrero); imposible -> error
    const string Sql_FactVentas =
@"WITH G AS (   -- lineas identicas: se conserva una sola
    SELECT [t_dat], [customer_id], [article_id], [price], [sales_channel_id], [TemporadaID], COUNT_BIG(*) AS [Lineas]
      FROM [HM].[StageTransactions]
     GROUP BY [t_dat], [customer_id], [article_id], [price], [sales_channel_id], [TemporadaID]),
V AS (
    SELECT G.*,
           COALESCE(TRY_CONVERT(DATE, t.[Fec], 112), TRY_CONVERT(DATE, t.[Fec], 23),
                    CASE WHEN t.[Fec] LIKE '%/%/%' THEN [DWH_HM].[dbo].[fn_LeerFecha](t.[Fec]) END) AS [FechaD],
           NULLIF(LTRIM(RTRIM(G.[customer_id])), '')                           AS [Cli],
           TRY_CONVERT(INT, LTRIM(RTRIM(G.[article_id])))                      AS [Art],
           COALESCE(TRY_CONVERT(FLOAT, t.[Pre]),
                    -- regla: la coma es separador decimal (si el valor trae una sola coma y ningun punto)
                    CASE WHEN t.[Pre] NOT LIKE '%.%' AND t.[Pre] NOT LIKE '%,%,%'
                         THEN TRY_CONVERT(FLOAT, REPLACE(t.[Pre], ',', '.')) END)  AS [P],
           TRY_CONVERT(TINYINT, LTRIM(RTRIM(G.[sales_channel_id])))            AS [Canal]
      FROM G
     -- NULLIF: un texto vacio es sin dato (TRY_CONVERT lo convertiria en 0 o en 1900-01-01)
     CROSS APPLY (SELECT NULLIF(LTRIM(RTRIM(G.[t_dat])), '') AS [Fec], NULLIF(LTRIM(RTRIM(G.[price])), '') AS [Pre]) t)
SELECT [t_dat] AS [t_dat_origen], [customer_id] AS [customer_id_origen], [article_id] AS [article_id_origen],
       [price] AS [price_origen], [sales_channel_id] AS [canal_origen], [TemporadaID] AS [temporada_origen],
       CONVERT(INT, CONVERT(CHAR(8), [FechaD], 112))                     AS [FechaNum],
       CAST(CASE WHEN LEN([Cli]) <= 64 THEN [Cli] END AS VARCHAR(64))    AS [CustomerID],
       [Art]                                                             AS [ArticleID],
       [Canal]                                                           AS [CanalID],
       CASE WHEN ABS([P]) < 1000000000
            THEN CAST(ROUND([P] * 40000, 4) AS DECIMAL(19,4)) END        AS [Precio],
       CAST([Lineas] AS INT)                                             AS [LineasOrigen],
       CAST(CASE WHEN [FechaD] IS NULL AND [t_dat] LIKE '%/%/%'
                      THEN N'Fecha inválida: ' + LEFT([t_dat], 30)
                 WHEN [FechaD] IS NULL THEN N'Fecha inválida: ' + ISNULL(LEFT([t_dat], 30), N'(vacía)')
                 WHEN [Cli] IS NULL    THEN N'Cliente vacío'
                 WHEN [Art] IS NULL    THEN N'Artículo inválido: ' + ISNULL(LEFT([article_id], 30), N'(vacío)')
                 WHEN [Canal] IS NULL  THEN N'Canal inválido: ' + ISNULL(LEFT([sales_channel_id], 30), N'(vacío)')
                 WHEN [P] IS NULL      THEN N'Precio vacío o no numérico: ' + ISNULL(LEFT([price], 30), N'(vacío)')
                 WHEN ABS([P]) >= 1000000000 THEN N'Precio fuera de rango: ' + LEFT([price], 30)
            END AS NVARCHAR(200))                                        AS [MotivoDescarte]
  FROM V";

    // Metas: Monto tal como viene en GoalsHyM (el x 40000 solo va en price, indicacion del profesor);
    // una meta repetida (mismo escenario, departamento, seccion, temporada y mes) se carga una sola vez
    const string Sql_FactMetas =
@"WITH S AS (
    SELECT [FilaOrigen], [Escenario], [Monto], [department_name], [section_name], [TemporadaID], [AnioMes],
           LEFT(NULLIF(LTRIM(RTRIM([Escenario])), N''), 30)                                         AS [Esc],
           CASE WHEN [Monto] >= 0 AND [Monto] < 1000000000 THEN CAST(ROUND([Monto], 4) AS DECIMAL(19,4)) END AS [MontoDec],
           LEFT(LTRIM(RTRIM([department_name])), 60)                                                AS [Dep],
           LEFT(LTRIM(RTRIM([section_name])), 60)                                                   AS [Sec],
           CASE WHEN [TemporadaID] = FLOOR([TemporadaID]) AND [TemporadaID] BETWEEN 1 AND 255
                THEN CONVERT(TINYINT, [TemporadaID]) END                                            AS [Temp],
           CASE WHEN [AnioMes] = FLOOR([AnioMes]) AND [AnioMes] BETWEEN 190001 AND 999912
                 AND [AnioMes] - FLOOR([AnioMes] / 100) * 100 BETWEEN 1 AND 12 THEN CONVERT(INT, [AnioMes]) END AS [AM]
      FROM [HM].[StageGoals]),
R AS (SELECT S.*, ROW_NUMBER() OVER (PARTITION BY [Esc], [Dep], [Sec], [Temp], [AM] ORDER BY [FilaOrigen]) AS [rn] FROM S)
SELECT [FilaOrigen], [Escenario] AS [escenario_origen], [Monto] AS [monto_origen], [department_name] AS [department_origen],
       [section_name] AS [section_origen], [TemporadaID] AS [temporada_origen], [AnioMes] AS [aniomes_origen],
       CAST([Esc] AS NVARCHAR(30)) AS [Escenario], [MontoDec],
       CAST([Dep] AS NVARCHAR(60)) AS [department_name], CAST([Sec] AS NVARCHAR(60)) AS [section_name],
       [Temp] AS [TemporadaID], [AM] AS [AnioMes],
       CAST(CASE WHEN [Esc] IS NULL      THEN N'Escenario vacío'
                 WHEN [Monto] IS NULL    THEN N'Monto vacío o no numérico'
                 WHEN [MontoDec] IS NULL THEN N'Monto negativo o fuera de rango'
                 WHEN [Temp] IS NULL     THEN N'Temporada vacía o inválida'
                 WHEN [AM] IS NULL       THEN N'Año-mes inválido'
                 WHEN [rn] > 1           THEN N'Meta repetida (se conservó la primera aparición)'
            END AS NVARCHAR(200)) AS [MotivoDescarte]
  FROM R";

    // ================================================================== DWH
    public void BuildDwh(string ispac)
    {
        P = Project.CreateProject();
        P.Name = "DWH_H&M";
        P.ProtectionLevel = DTSProtectionLevel.DontSaveSensitive;

        AddConn("OLEDB", "OleDB DWH_HM", OleDbCs("DWH_HM"));
        AddConn("OLEDB", "OleDB STAGE_HM", OleDbCs("STAGE_HM"));
        AddConn(AdoType, "AdoNet DWH_HM", AdoCs("DWH_HM"));

        // Dimensiones: cada paquete ejecuta su procedimiento (limpieza + ErrorMaestro + MERGE, ver 02_crear_DWH_HM.sql)
        foreach (string[] dim in new[] { new[] { "GENERICO", "DimFecha" }, new[] { "Ventas", "DimTemporada" }, new[] { "Ventas", "DimCanal" },
                                         new[] { "Ventas", "DimDepartamento" }, new[] { "Ventas", "DimArticulo" }, new[] { "Ventas", "DimCliente" } })
        {
            string table = "[" + dim[0] + "].[" + dim[1] + "]";
            Package pkg = NewPackage(dim[1], table);
            // el SP recibe el AuditKey para registrar cuantas filas inserto y actualizo su MERGE
            TaskHost sp = Sql(pkg, "Execute sp_" + dim[1], C(pkg, "AdoNet DWH_HM"),
                              "EXEC [" + dim[0] + "].[sp_" + dim[1] + "] @AuditKey = @AuditKey;");
            Param((ExecuteSQLTask)sp.InnerObject, "AuditKey", "User::AuditKey", DbInt32);
            Template(pkg, "AdoNet DWH_HM", table, null, sp);
        }

        {   // FactVentas
            Package pkg = NewPackage("FactVentas", "[Ventas].[FactVentas]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "FACT VENTAS", out th);
            ConnectionManager dwh = C(pkg, "OleDB DWH_HM");
            var src = OleSource(mp, "Origen de OLE DB", C(pkg, "OleDB STAGE_HM"), Sql_FactVentas);
            var l1 = Lookup(mp, "DimFecha", dwh, "SELECT [FechaKey] FROM [GENERICO].[DimFecha] WHERE [FechaKey] > 0", src.OutputCollection[0],
                new[] { new[] { "FechaNum", "FechaKey" } }, new[] { new[] { "FechaKey", "FechaKey" } }, false);
            var l2 = Lookup(mp, "DimCliente", dwh, "SELECT [ClienteKey], [CustomerID] FROM [Ventas].[DimCliente] WHERE [ClienteKey] > 0", l1.OutputCollection[0],
                new[] { new[] { "CustomerID", "CustomerID" } }, new[] { new[] { "ClienteKey", "ClienteKey" } }, false);
            var l3 = Lookup(mp, "DimArticulo", dwh, "SELECT [ArticuloKey], [DepartamentoKey], [ArticleID] FROM [Ventas].[DimArticulo] WHERE [ArticuloKey] > 0", l2.OutputCollection[0],
                new[] { new[] { "ArticleID", "ArticleID" } },
                new[] { new[] { "ArticuloKey", "ArticuloKey" }, new[] { "DepartamentoKey", "DepartamentoKey" } }, false);
            var l4 = Lookup(mp, "DimCanal", dwh, "SELECT [CanalKey], [CanalID] FROM [Ventas].[DimCanal] WHERE [CanalKey] > 0", l3.OutputCollection[0],
                new[] { new[] { "CanalID", "CanalID" } }, new[] { new[] { "CanalKey", "CanalKey" } }, false);
            // la temporada se deduce de la FECHA (no se confia en la columna TemporadaID del archivo);
            // el dia en que se cruzan dos temporadas pertenece a la que termina, igual que en el archivo original
            var l5 = Lookup(mp, "DimTemporada (por fecha)", dwh,
@"SELECT f.[FechaKey], t.[TemporadaKey]
  FROM [GENERICO].[DimFecha] f
 CROSS APPLY (SELECT TOP (1) d.[TemporadaKey] FROM [Ventas].[DimTemporada] d
               WHERE d.[TemporadaKey] > 0 AND f.[Fecha] BETWEEN d.[FechaInicio] AND d.[FechaFin]
               ORDER BY d.[FechaFin]) t
 WHERE f.[FechaKey] > 0", l4.OutputCollection[0],
                new[] { new[] { "FechaKey", "FechaKey" } }, new[] { new[] { "TemporadaKey", "TemporadaKey" } }, false);
            var keys = new[] { "FechaKey", "ClienteKey", "ArticuloKey", "DepartamentoKey", "CanalKey", "TemporadaKey" };
            var cs = BadSplit(mp, l5.OutputCollection[0], keys);
            var mot = MotivoColumn(mp, Out(cs, "bad"), new[] {
                new[] { "FechaKey", "Fecha fuera del calendario (no existe en DimFecha)" },
                new[] { "ClienteKey", "Cliente inexistente en DimCliente" },
                new[] { "ArticuloKey", "Artículo inexistente en DimArticulo" },
                new[] { "CanalKey", "Canal inexistente en DimCanal" },
                new[] { "TemporadaKey", "La fecha no cae en ninguna temporada de DimTemporada" } });
            OleDest(mp, "ErrorFactVentas", dwh, "[Ventas].[ErrorFactVentas]", mot.OutputCollection[0], null, false);
            var factMap = keys.ToDictionary(k => k, k => k);
            factMap["Precio"] = "Precio"; factMap["LineasOrigen"] = "LineasOrigen";
            OleDest(mp, "FactVentas", dwh, "[Ventas].[FactVentas]", DefaultOut(cs), factMap, true);
            Template(pkg, "AdoNet DWH_HM", "[Ventas].[FactVentas]",
                "TRUNCATE TABLE [Ventas].[FactVentas];\r\nTRUNCATE TABLE [Ventas].[ErrorFactVentas];", th);
        }

        {   // FactMetas (GoalsHyM.xlsx)
            Package pkg = NewPackage("FactMetas", "[Ventas].[FactMetas]");
            TaskHost th; MainPipe mp = DataFlow(pkg, "FACT METAS", out th);
            ConnectionManager dwh = C(pkg, "OleDB DWH_HM");
            var src = OleSource(mp, "Origen de OLE DB", C(pkg, "OleDB STAGE_HM"), Sql_FactMetas);
            var l1 = Lookup(mp, "DimDepartamento", dwh, "SELECT [DepartamentoKey], [department_name], [section_name] FROM [Ventas].[DimDepartamento] WHERE [DepartamentoKey] > 0",
                src.OutputCollection[0], new[] { new[] { "department_name", "department_name" }, new[] { "section_name", "section_name" } },
                new[] { new[] { "DepartamentoKey", "DepartamentoKey" } }, false);
            var l2 = Lookup(mp, "DimTemporada", dwh, "SELECT [TemporadaKey], [TemporadaID] FROM [Ventas].[DimTemporada] WHERE [TemporadaKey] > 0", l1.OutputCollection[0],
                new[] { new[] { "TemporadaID", "TemporadaID" } }, new[] { new[] { "TemporadaKey", "TemporadaKey" } }, false);
            var l3 = Lookup(mp, "DimFecha (mes)", dwh,
                "SELECT MIN([FechaKey]) AS [FechaKey], [AnioMes] FROM [GENERICO].[DimFecha] WHERE [FechaKey] > 0 GROUP BY [AnioMes]",
                l2.OutputCollection[0], new[] { new[] { "AnioMes", "AnioMes" } }, new[] { new[] { "FechaKey", "FechaKey" } }, false);
            var keys = new[] { "DepartamentoKey", "TemporadaKey", "FechaKey" };
            var cs = BadSplit(mp, l3.OutputCollection[0], keys);
            var mot = MotivoColumn(mp, Out(cs, "bad"), new[] {
                new[] { "DepartamentoKey", "Departamento/sección inexistente en DimDepartamento" },
                new[] { "TemporadaKey", "Temporada inexistente en DimTemporada" },
                new[] { "FechaKey", "Mes fuera del calendario (no existe en DimFecha)" } });
            OleDest(mp, "ErrorFactMetas", dwh, "[Ventas].[ErrorFactMetas]", mot.OutputCollection[0], null, false);
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
        OnErrorAudit(pkg, adoDwh);
    }
}
