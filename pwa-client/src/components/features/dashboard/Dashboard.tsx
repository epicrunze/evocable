'use client';

import { Layout } from '@/components/common/Layout';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { 
  BookOpenIcon, 
  UploadIcon,
  ClockIcon,
  HardDriveIcon
} from 'lucide-react';

export function Dashboard() {
  return (
    <Layout currentPage="library">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Books</CardTitle>
            <BookOpenIcon className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-gray-500">
              No books in your library yet
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Duration</CardTitle>
            <ClockIcon className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0h 0m</div>
            <p className="text-xs text-gray-500">
              Total audiobook time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <HardDriveIcon className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0 MB</div>
            <p className="text-xs text-gray-500">
              of unlimited storage
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Area */}
      <Card>
        <CardHeader>
          <CardTitle>Your Audiobook Library</CardTitle>
          <CardDescription>
            Upload documents to convert them into audiobooks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No books yet
            </h3>
            <p className="text-gray-500 mb-6 max-w-sm mx-auto">
              Ready to create your first audiobook? Upload a PDF, EPUB, or TXT file to get started.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              <Button className="flex items-center space-x-2">
                <UploadIcon className="h-4 w-4" />
                <span>Upload Your First Book</span>
              </Button>
              <Badge variant="info" className="text-xs">
                Supported: PDF, EPUB, TXT
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity Section */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Your latest uploads and conversions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <ClockIcon className="mx-auto h-8 w-8 mb-2 text-gray-400" />
            <p>No recent activity</p>
          </div>
        </CardContent>
      </Card>
    </Layout>
  );
} 