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
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password required'),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setLoading(true)
    try {
      const form = new URLSearchParams()
      form.append('username', data.email)
      form.append('password', data.password)
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/login`,
        form,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )
      localStorage.setItem('edu_token', res.data.access_token)
      localStorage.setItem('edu_user', JSON.stringify(res.data.user))
      router.push('/dashboard')
    } catch {
      toast.error('Invalid email or password')
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
            <h1 className="text-2xl font-syne font-bold text-gray-900">EduSchedule</h1>
            <p className="text-sm text-gray-500 mt-1">Sign in to your account</p>
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="admin@eduschedule.com"
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register('password')}
            />
            <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
              Sign in
            </Button>
          </form>
          <p className="text-center text-xs text-gray-500 mt-6 font-mono">
            admin@eduschedule.com / Admin@123
          </p>
        </div>
      </div>
    </>
  )
}
