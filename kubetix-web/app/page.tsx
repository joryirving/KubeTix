"use client"

import { useState, useEffect } from "react"
import axios from "axios"
import { formatDistanceToNow } from "date-fns"
import { 
  Key, 
  Clock, 
  Shield, 
  Copy, 
  Check, 
  AlertCircle,
  Plus,
  X
} from "lucide-react"

interface Grant {
  id: string
  cluster_name: string
  namespace: string | null
  role: string
  created_at: string
  expires_at: string
  revoked: boolean
}

export default function Home() {
  const [grants, setGrants] = useState<Grant[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  
  // Form state
  const [clusterName, setClusterName] = useState("prod")
  const [namespace, setNamespace] = useState("")
  const [role, setRole] = useState("view")
  const [expiry, setExpiry] = useState(4)

  useEffect(() => {
    fetchGrants()
  }, [])

  const fetchGrants = async () => {
    try {
      // In production, this would call your API
      // const response = await axios.get(`${process.env.API_URL}/grants`)
      // setGrants(response.data)
      
      // Mock data for now
      const mockGrants: Grant[] = [
        {
          id: "HVxTHVGn6413wnB5RL_L2w",
          cluster_name: "prod",
          namespace: "production",
          role: "edit",
          created_at: new Date(Date.now() - 3600000).toISOString(),
          expires_at: new Date(Date.now() + 3 * 3600000).toISOString(),
          revoked: false
        }
      ]
      setGrants(mockGrants)
    } catch (error) {
      console.error("Failed to fetch grants:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateGrant = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      // In production, this would call your API
      // await axios.post(`${process.env.API_URL}/grants`, {
      //   cluster_name: clusterName,
      //   namespace: namespace || null,
      //   role,
      //   expiry_hours: expiry
      // })
      
      // Mock success
      setShowCreateModal(false)
      fetchGrants()
    } catch (error) {
      console.error("Failed to create grant:", error)
    }
  }

  const handleRevoke = async (grantId: string) => {
    try {
      // In production, this would call your API
      // await axios.delete(`${process.env.API_URL}/grants/${grantId}`)
      
      setGrants(grants.filter(g => g.id !== grantId))
    } catch (error) {
      console.error("Failed to revoke grant:", error)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(text)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "admin": return "bg-red-100 text-red-800"
      case "edit": return "bg-yellow-100 text-yellow-800"
      default: return "bg-green-100 text-green-800"
    }
  }

  const getTimeRemaining = (expiresAt: string) => {
    const now = new Date()
    const expiry = new Date(expiresAt)
    const diff = expiry.getTime() - now.getTime()
    
    if (diff <= 0) return "Expired"
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m remaining`
    return `${Math.floor(diff / 3600000)}h remaining`
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="bg-primary-500 p-2 rounded-lg">
                <Key className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">KubeTix</h1>
                <p className="text-sm text-gray-500">Temporary Kubernetes Access</p>
              </div>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Create Grant</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 p-2 rounded-lg">
                <Key className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Active Grants</p>
                <p className="text-2xl font-bold text-gray-900">{grants.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-3">
              <div className="bg-yellow-100 p-2 rounded-lg">
                <Clock className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Auto-Expiry</p>
                <p className="text-2xl font-bold text-gray-900">On</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-3">
              <div className="bg-green-100 p-2 rounded-lg">
                <Shield className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Encryption</p>
                <p className="text-2xl font-bold text-gray-900">AES-128</p>
              </div>
            </div>
          </div>
        </div>

        {/* Grants List */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Active Grants</h2>
          </div>
          
          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
              <p className="mt-2 text-gray-500">Loading grants...</p>
            </div>
          ) : grants.length === 0 ? (
            <div className="p-8 text-center">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 mb-4">No active grants</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg"
              >
                Create Your First Grant
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {grants.map((grant) => (
                <div key={grant.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{grant.cluster_name}</h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(grant.role)}`}>
                          {grant.role}
                        </span>
                        {grant.namespace && (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {grant.namespace}
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center space-x-4 text-sm text-gray-500 mb-3">
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{getTimeRemaining(grant.expires_at)}</span>
                        </div>
                        <div>
                          Created {formatDistanceToNow(new Date(grant.created_at), { addSuffix: true })}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <code className="bg-gray-100 px-3 py-1 rounded text-sm text-gray-700">
                          {grant.id}
                        </code>
                        <button
                          onClick={() => copyToClipboard(grant.id)}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          title="Copy ID"
                        >
                          {copiedId === grant.id ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleRevoke(grant.id)}
                      className="text-red-600 hover:text-red-800 p-2 hover:bg-red-50 rounded-lg transition-colors"
                      title="Revoke Grant"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create Grant Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">Create Grant</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            <form onSubmit={handleCreateGrant} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cluster Name
                </label>
                <input
                  type="text"
                  value={clusterName}
                  onChange={(e) => setClusterName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="prod"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Namespace (optional)
                </label>
                <input
                  type="text"
                  value={namespace}
                  onChange={(e) => setNamespace(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="production"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="view">View</option>
                  <option value="edit">Edit</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expiry (hours)
                </label>
                <select
                  value={expiry}
                  onChange={(e) => setExpiry(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value={1}>1 hour</option>
                  <option value={4}>4 hours</option>
                  <option value={8}>8 hours</option>
                  <option value={24}>24 hours</option>
                  <option value={168}>7 days</option>
                </select>
              </div>
              
              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                >
                  Create Grant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
