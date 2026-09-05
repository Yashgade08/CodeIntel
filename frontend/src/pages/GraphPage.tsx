import React, { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  GitFork,
  Search,
  Layers,
  FileCode,
  ArrowRight,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

const CustomFileNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as any;
  const riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' = nodeData.risk_level || 'LOW';

  const borderColors: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
    LOW: 'border-slate-700 hover:border-emerald-500',
    MEDIUM: 'border-amber-800/80 hover:border-amber-500',
    HIGH: 'border-rose-800/80 hover:border-rose-500',
  };

  return (
    <div
      className={`glass-panel p-3 rounded-xl min-w-[180px] shadow-lg transition-all border-2 ${
        borderColors[riskLevel]
      } ${selected ? 'ring-2 ring-cyan-400 border-cyan-400 shadow-cyan-500/20' : ''}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-400 !w-2.5 !h-2.5" />
      <div className="flex items-center space-x-2">
        <FileCode
          className={`h-4 w-4 ${
            riskLevel === 'HIGH' ? 'text-rose-400' : riskLevel === 'MEDIUM' ? 'text-amber-400' : 'text-cyan-400'
          }`}
        />
        <div className="truncate">
          <div className="text-xs font-bold font-mono text-slate-100 truncate">{nodeData.label}</div>
          <div className="text-[10px] text-slate-400 font-mono">Risk: {nodeData.risk_score || 20}/100</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-indigo-400 !w-2.5 !h-2.5" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomFileNode,
};

export const GraphPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string>('app/rag/pipeline.py');

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['dependencyGraph', id],
    queryFn: () => apiService.getDependencyGraph(id),
  });

  const { data: fileImpact } = useQuery({
    queryKey: ['fileImpact', id, selectedNodeId],
    queryFn: () => apiService.getFileDependencies(id, selectedNodeId),
  });

  const initialNodes = useMemo(() => {
    return (graphData?.nodes || []).map((node) => ({
      ...node,
      type: 'custom',
    }));
  }, [graphData]);

  const initialEdges = useMemo(() => {
    return graphData?.edges || [];
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any);

  React.useEffect(() => {
    if (graphData?.nodes) {
      setNodes(graphData.nodes.map((n) => ({ ...n, type: 'custom' })) as any);
    }
    if (graphData?.edges) {
      setEdges(graphData.edges as any);
    }
  }, [graphData, setNodes, setEdges]);

  const handleNodeClick = (_: any, node: any) => {
    setSelectedNodeId(node.id || node.data.path);
  };

  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    return nodes.filter((n: any) =>
      n.id.toLowerCase().includes(searchTerm.toLowerCase()) || n.data.label.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [nodes, searchTerm]);

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] space-y-4">
      {/* Top Header & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between glass-panel p-4 rounded-2xl border border-slate-800 gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-purple-950/80 text-purple-400 border border-purple-800">
            <GitFork className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <span>Repository Dependency Graph</span>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase bg-purple-950 text-purple-300 border border-purple-800 rounded-full">
                NetworkX AST DAG
              </span>
            </h1>
            <p className="text-xs text-slate-400">Interactive module call relationships, dependent nodes & impact radius</p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search module path..."
            className="w-full bg-slate-950 text-xs text-slate-100 placeholder-slate-500 border border-slate-800 rounded-xl pl-9 pr-3 py-2 focus:outline-none focus:border-purple-500 font-mono"
          />
        </div>
      </div>

      {/* React Flow Canvas + Inspector Drawer Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* React Flow Canvas (8 cols) */}
        <div className="lg:col-span-8 glass-panel rounded-2xl border border-slate-800 overflow-hidden relative">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950 text-xs font-mono text-purple-400">
              <Loader2 className="h-5 w-5 animate-spin mr-2" /> Constructing NetworkX DAG...
            </div>
          ) : (
            <ReactFlow
              nodes={filteredNodes as any}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={handleNodeClick}
              nodeTypes={nodeTypes}
              fitView
            >
              <Background color="#1e293b" gap={20} size={1} />
              <Controls />
            </ReactFlow>
          )}
        </div>

        {/* Node Inspector Drawer (4 cols) */}
        <div className="lg:col-span-4 glass-panel rounded-2xl border border-slate-800 p-5 overflow-y-auto space-y-6">
          <div className="space-y-2 border-b border-slate-900 pb-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Selected Node</span>
            <h2 className="text-base font-bold text-slate-100 font-mono break-all">{selectedNodeId}</h2>
            <RiskLevelBadge level="HIGH" score={84} />
          </div>

          {/* "What depends on this file?" */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center space-x-1.5">
              <GitFork className="h-4 w-4" />
              <span>What depends on this file? (Dependents)</span>
            </h3>

            <div className="space-y-1.5 text-xs font-mono">
              {fileImpact?.dependents && fileImpact.dependents.length > 0 ? (
                fileImpact.dependents.map((dep, idx) => (
                  <div key={idx} className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-purple-300 flex items-center justify-between">
                    <span className="truncate">{dep}</span>
                    <ArrowRight className="h-3 w-3 text-slate-500 flex-shrink-0 ml-1" />
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 p-2 font-mono">No downstream dependents</div>
              )}
            </div>
          </div>

          {/* "What does this file depend on?" */}
          <div className="space-y-3 pt-2 border-t border-slate-900">
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
              <Layers className="h-4 w-4" />
              <span>What does this file depend on? (Imports)</span>
            </h3>

            <div className="space-y-1.5 text-xs font-mono">
              {fileImpact?.dependencies && fileImpact.dependencies.length > 0 ? (
                fileImpact.dependencies.map((dep, idx) => (
                  <div key={idx} className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-cyan-300 flex items-center justify-between">
                    <span className="truncate">{dep}</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 p-2 font-mono">No external imports</div>
              )}
            </div>
          </div>

          {/* Affected Module Radius */}
          <div className="space-y-2 pt-2 border-t border-slate-900">
            <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-1.5">
              <ShieldAlert className="h-4 w-4" />
              <span>Impact Radius (Refactor Risk)</span>
            </h3>
            <p className="text-xs text-slate-400 leading-normal">
              Changing <code className="text-cyan-300">{selectedNodeId}</code> may require regression testing on <strong>{fileImpact?.affected_modules.length || 3}</strong> modules.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
