'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { Toaster } from 'react-hot-toast'
import axios from 'axios'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const schema = z.object({
  current_password: z.string().min(1, 'Current password required'),
  new_password: z.string().min(10, 'At least 10 characters'),
  new_password_confirm: z.string().min(10),
}).refine((d) => d.new_password === d.new_password_confirm, {
  message: 'Passwords do not match',
  path: ['new_password_confirm'],
}).refine((d) => d.new_password !== d.current_password, {
  message: 'New password must be different from current',
  path: ['new_password'],
})

type FormData = z.infer<typeof schema>

export default function ChangePasswordPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setLoading(true)
    try {
      const token = localStorage.getItem('edu_token')
      if (!token) {
        router.replace('/login')
        return
      }
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/change-password`,
        {
          current_password: data.current_password,
          new_password: data.new_password,
        },
        { headers: { Authorization: `Bearer ${token}` } },
      )
      // Refresh the cached user block so the app knows the flag is cleared.
      const raw = localStorage.getItem('edu_user')
      if (raw) {
        const parsed = JSON.parse(raw)
        parsed.must_change_password = false
        localStorage.setItem('edu_user', JSON.stringify(parsed))
      }
      toast.success('Password updated')
      router.replace('/dashboard')
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (status === 401) toast.error('Current password is incorrect')
      else toast.error(detail ?? 'Could not update password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Toaster position="top-right" />
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-xl border border-gray-200 shadow-md p-8">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-syne font-bold text-gray-900">Set a new password</h1>
            <p className="text-sm text-gray-500 mt-2">
              Your current password is a shared default that was exposed in a
              public git history. Choose a new one before continuing.
            </p>
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Current password"
              type="password"
              placeholder="••••••••"
              error={errors.current_password?.message}
              {...register('current_password')}
            />
            <Input
              label="New password"
              type="password"
              placeholder="At least 10 characters"
              error={errors.new_password?.message}
              {...register('new_password')}
            />
            <Input
              label="Confirm new password"
              type="password"
              placeholder="••••••••"
              error={errors.new_password_confirm?.message}
              {...register('new_password_confirm')}
            />
            <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
              Update password
            </Button>
          </form>
        </div>
      </div>
    </>
  )
}
